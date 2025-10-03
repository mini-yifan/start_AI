#!/usr/bin/python3
# -*- coding: utf-8 -*-

import json
import asyncio
import os
import time
from typing import List, Dict
from datetime import datetime

from openai import OpenAI
from fastmcp import Client
from tts import realtime_tts_speak
from tts2 import realtime_tts_speak2
from asr2 import speech_to_text
import re
from prompt_tone import DingPlayer

import pyaudio
from vosk import Model, KaldiRecognizer
import json
import re
from dotenv import load_dotenv
import random

load_dotenv()  # 默认会加载根目录下的.env文件

class MCPClient:
    def __init__(self, script: str, model="qwen-plus", max_tool_calls=1):
        self.script = script
        self.model = model
        self.max_tool_calls = max_tool_calls  # 每个工具的最大调用次数

        self.client = OpenAI(
            # 若没有配置环境变量，请用阿里云百炼API Key将下行替换为：api_key="sk-xxx",
            api_key=os.getenv("ALIBABA_CLOUD_ACCESS_KEY_ID"),
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1"
        )

        self.session = Client(script)
        self.tools = []
        self.tool_call_count = {}  # 记录每个工具的调用次数

    def read_ai_setting_file(file_path="ai_setting.txt"):
        """
        读取txt文件内容
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                # 读取文件内容
                content = file.read()
                return content
        except FileNotFoundError:
            return "文件未找到"
        except Exception as e:
            return f"读取文件时出错: {str(e)}"

    async def prepare_tools(self):
        tools = await self.session.list_tools()
        self.tools = [
            {
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "input_schema": tool.inputSchema
                }
            }
            for tool in tools
        ]

    async def chat(self, messages: List[Dict], tool_call_path=None):
        if tool_call_path is None:
            tool_call_path = []  # 记录调用路径，防止重复调用

        if not self.tools:
            await self.prepare_tools()

        content2 = None
        with open("ai_setting.txt", 'r', encoding='utf-8') as file:
            # 读取文件内容
            content2 = file.read()

        # 添加系统消息
        system_message = {
            "role": "system",
            "content": "你叫是语音助手，用来解决用户问题，你的回答简短而有力，不拖泥带水。回答问题尽量吧回答控制在200字以以内。"+content2
        }
        #print(system_message)

        # 确保系统消息在消息列表的开头
        if messages and messages[0].get("role") != "system":
            messages = [system_message] + messages
        elif not messages:
            messages = [system_message]

        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            tools=self.tools,
            max_tokens=1024,
        )

        if response.choices[0].finish_reason != 'tool_calls':
            return response.choices[0].message

        # 调用工具
        for tool_call in response.choices[0].message.tool_calls:
            tool_name = tool_call.function.name

            # 检查该工具是否已超过最大调用次数
            if tool_name in self.tool_call_count and self.tool_call_count[tool_name] >= self.max_tool_calls:
                # 如果超过限制，返回错误信息给模型
                error_message = f"工具 {tool_name} 已达到最大调用次数限制 ({self.max_tool_calls}次)，无法继续调用。"
                messages.append({
                    'role': 'assistant',
                    'content': error_message
                })
                # 让模型基于错误信息生成回复
                return await self.chat(messages, tool_call_path)

            # 增加工具调用计数
            if tool_name in self.tool_call_count:
                self.tool_call_count[tool_name] += 1
            else:
                self.tool_call_count[tool_name] = 1

            # 检查是否在调用路径中已经存在，防止循环调用
            tool_call_id = f"{tool_name}_{tool_call.function.arguments}"
            if tool_call_id in tool_call_path:
                error_message = f"检测到循环调用 {tool_name}，已阻止重复调用。"
                messages.append({
                    'role': 'assistant',
                    'content': error_message
                })
                return await self.chat(messages, tool_call_path)

            # 添加到调用路径
            tool_call_path.append(tool_call_id)

            # 调用工具
            try:
                result = await self.session.call_tool(tool_name, json.loads(tool_call.function.arguments))
                messages.append({
                    'role': 'assistant',
                    'content': result.content[0].text if result.content else "工具调用完成"
                })
            except Exception as e:
                error_message = f"工具 {tool_name} 调用出错: {str(e)}"
                messages.append({
                    'role': 'assistant',
                    'content': error_message
                })

            return await self.chat(messages, tool_call_path)

        return response

    async def loop(self):
        num_i = 1
        player = DingPlayer(frequency=600, duration_ms=100)

        # 初始化英文唤醒模型
        model = Model('vosk-model-small-en-us-0.15')
        audio_interface = pyaudio.PyAudio()
        audio_stream = audio_interface.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=16000,
            input=True,
            frames_per_buffer=4000,
        )
        recognizer = KaldiRecognizer(model, 16000)
        print("开始识别")
        while True:
            data = audio_stream.read(4000)
            if len(data) == 0:
                break
            if recognizer.AcceptWaveform(data):
                result = json.loads(recognizer.Result())
                text = result["text"]
                #print(text)
                # 使用正则表达式识别是否有hello
                if re.search(r'\bhello\s[tcdjh]', text, re.IGNORECASE) or num_i == 1:
                    if num_i == 1:
                        realtime_tts_speak("正在初始化，听到“哔”声后喊hello jarvis，就可以对话了", rate=28000)
                    else:
                        print("已正确识别")
                        realtime_tts_speak("乐意效劳。", rate=28000)
                    #break
                    while True:
                        async with self.session:
                            if num_i == 1:
                                num_i = num_i + 1
                                player.play()
                                time.sleep(0.5)
                                break
                            player.play()
                            time.sleep(0.5)
                            #player.quit()

                            question = speech_to_text()
                            # question = input("用户输入：")
                            if question == None:
                                realtime_tts_speak("我先退出了 ，先生。", rate=26000)
                                break
                            player.play()
                            time.sleep(0.2)
                            player.play()
                            time.sleep(0.3)

                            # 重置工具调用计数器（每次用户提问时重置）
                            self.tool_call_count = {}

                            if re.search(r'[贾艾简]维斯[,，]?\s*(退出|推出|你可以退出了)', question) or re.search(r'退出程序', question):
                                realtime_tts_speak("好的，已退出，随时待命。", rate=27000)
                                break

                            # 设置超时时间为30秒
                            start_time = time.time()
                            try:
                                current_time = "当前时间为："+datetime.today().strftime('%Y.%m.%d %H时%M分%S秒')+"\n"
                                question = current_time+ "用户问题：" + question
                                response = await asyncio.wait_for(
                                    self.chat([
                                        {
                                            "role": "user",
                                            "content": question,
                                        }
                                    ]),
                                    timeout=120.0  # 120秒超时
                                )
                            except asyncio.TimeoutError:
                                print("请求超时，重新进入循环")
                                realtime_tts_speak("请求超时，重新进入循环", rate=27000)
                                break  # 跳出内部循环，重新进入唤醒检测循环

                            # 检查response是否有内容
                            if not hasattr(response, 'content') or response.content is None:
                                print("无响应内容，重新进入循环")
                                realtime_tts_speak("无响应内容，重新进入循环", rate=27000)
                                break  # 跳出内部循环，重新进入唤醒检测循环

                            print(f"AI: {response.content}")
                            # 删除内容中的网页链接
                            cleaned_content = re.sub(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', '', response.content)
                            # 清理多余的空格
                            cleaned_content = re.sub(r'\s+', ' ', cleaned_content).strip()
                            print(len(cleaned_content))
                            if len(cleaned_content)<25:
                                realtime_tts_speak(cleaned_content)
                            else:
                                #realtime_tts_speak2(cleaned_content)

                                # 将内容进行分句, 避免AI听到自己说话
                                # 定义要拆分的标点符号
                                punctuation = "，。/？.,!\""
                                # 转义特殊字符并构建正则表达式模式
                                pattern = f"[{re.escape(punctuation)}]"
                                # 找到所有匹配的位置
                                matches = list(re.finditer(pattern, cleaned_content))
                                if len(matches) > 2:
                                    # 获取第1个匹配的位置
                                    second_last_match = matches[-2]
                                    # 分割成两个部分
                                    first_part = cleaned_content[:second_last_match.end()]
                                    second_part = cleaned_content[second_last_match.end():]
                                    # 清理两部分的空白字符
                                    first_part = first_part.strip()
                                    second_part = second_part.strip()
                                    # 过滤掉空字符串
                                    result_sentence = [s for s in [first_part, second_part] if s]
                                    print(result_sentence)
                                    rr = realtime_tts_speak2(result_sentence[0]+"......")
                                    if rr != 1:
                                        realtime_tts_speak(result_sentence[1])
                                    else:
                                        realtime_tts_speak("嗯。", rate=24000)
                                    # if rr==1:
                                    #     realtime_tts_speak("嗯。", rate=24000)
                                    # else:
                                    #     random_speeches = [
                                    #         lambda: realtime_tts_speak("嗯。", rate=24000),
                                    #         lambda: realtime_tts_speak("还有什么，尽管问我。", rate=28000),
                                    #         lambda: realtime_tts_speak("我说完了，随时待命。", rate=27000),
                                    #         lambda: realtime_tts_speak("我讲完了，随时效劳。", rate=27000)
                                    #     ]
                                    #     random.choice(random_speeches)()
                                else:
                                    # 如果匹配少于3个，则返回原文本
                                    realtime_tts_speak(cleaned_content)
                                    time.sleep(1)

    def get_tool_call_stats(self):
        """
        获取工具调用统计信息
        """
        return self.tool_call_count.copy()

    def reset_tool_call_count(self):
        """
        重置所有工具调用计数
        """
        self.tool_call_count = {}

async def main():
    mcp_client = MCPClient("http://localhost:9000/mcp", max_tool_calls=1)
    await mcp_client.loop()


if __name__ == '__main__':
    asyncio.run(main())



