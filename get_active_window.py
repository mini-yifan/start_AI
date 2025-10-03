import win32com.client
import time
import win32gui
import win32process
import platform
import psutil
import re
import pyperclip
import os
import subprocess
import pyautogui
import platform
from summarize_write_ai import get_file_summary, code_ai_explain_model

def write_and_open_txt(ai_content, file_path="file_summary\\summary.txt"):
    # 将内容写入文件并打开记事本
    with open(file_path, 'w', encoding='utf-8') as file:
        file.write(ai_content)
    print(f"内容已写入 {file_path}")

    # 根据不同操作系统打开文件
    system = platform.system()

    if system == "Windows":
        # Windows系统重启记事本并打开文件
        try:
            # 强制终止现有的记事本进程及子进程
            subprocess.run(["taskkill", "/f", "/t", "/im", "notepad.exe"],
                         stderr=subprocess.DEVNULL, stdout=subprocess.DEVNULL)
            print("已强制终止现有的记事本进程。")
        except Exception as e:
            print("无法强制终止现有的记事本进程。")

        # 等待一段时间确保进程已结束
        time.sleep(0.5)

        # 启动记事本并打开文件
        subprocess.Popen(["notepad.exe", file_path])
    else:
        print(f"无法自动打开文件，请手动打开: {file_path}")


def get_active_window_title():
    """
    获取当前活动窗口的标题（仅支持Windows）

    Returns:
        str: 活动窗口标题，如果无法获取则返回空字符串
    """
    system = platform.system()
    if system == "Windows":
        try:
            # 获取当前活动窗口句柄
            hwnd = win32gui.GetForegroundWindow()
            # 获取窗口标题
            window_title = win32gui.GetWindowText(hwnd)
            # 获取窗口所属进程ID
            _, pid = win32process.GetWindowThreadProcessId(hwnd)

            return window_title, pid
        except ImportError:
            print("需要安装pywin32库: pip install pywin32")
            return "", None
        except Exception as e:
            print(f"获取活动窗口信息时出错: {e}")
            return "", None
    else:
        print("此功能主要支持Windows系统")
        return "", None

def get_active_window_info():
    """
    获取当前活动窗口的详细信息

    Returns:
        dict: 包含活动窗口信息的字典
    """
    info = {
        'window_title': '',
        'process_name': '',
        'pid': None
    }
    window_title, pid = get_active_window_title()
    info['window_title'] = window_title
    info['pid'] = pid

    if pid:
        try:
            process = psutil.Process(pid)
            process_name = process.name().lower()
            info['process_name'] = process_name
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    return info

def ai_summary_and_open_txt(file_content, file_path="file_summary\\summary.txt"):
    """
    对文件内容进行AI摘要总结，并将结果写入指定文件，然后尝试打开该文件

    :param file_content: 要进行摘要的原始文件内容
    :param file_path: 摘要结果保存的文件路径，默认为"file_summary\\summary.txt"
    :return: 成功时返回AI摘要内容，失败时返回错误提示信息
    """
    ai_summary_content = get_file_summary(file_content)
    try:
        # 将内容写入文件
        with open(file_path, 'w', encoding='utf-8') as file:
            file.write(ai_summary_content)
        print(f"内容已写入 {file_path}")

        # 根据不同操作系统打开文件
        system = platform.system()

        if system == "Windows":
            # Windows系统使用默认程序打开文件
            os.startfile(file_path)
        else:
            print(f"无法自动打开文件，请手动打开: {file_path}")
        return ai_summary_content

    except Exception as e:
        print(f"写入或打开文件时出错: {e}")
        return "总结文件时出错。"

def ai_explain_and_open_txt(file_content, file_path="file_summary\\code.txt"):
    """
    使用AI模型对文件内容进行解释分析，并将结果写入文本文件后打开
    :param file_content: 需要AI解释的文件内容字符串
    :param file_path: 保存AI解释结果的文件路径，默认为"file_summary\\code.txt"
    :return: AI模型生成的解释内容字符串
    """
    # 调用AI模型对代码内容进行解释
    ai_explain_content = code_ai_explain_model(file_content)
    try:
        # 将AI解释内容写入文件并打开
        write_and_open_txt(ai_explain_content, file_path)
    except Exception as e:
        print(f"写入或打开文件时出错: {e}")
    return ai_explain_content


def get_activate_path():
    """
    获取当前活动窗口的文件路径和内容信息
    Returns:
        dict: 包含文件信息和内容的字典
    """
    # 获取当前活动窗口句柄
    window_title, pid = get_active_window_title()
    info = get_active_window_info()
    print("info", info)

    # 初始化结果字典
    result_file_content = {
        'file_name': '',
        'file_path': '',
        'file_type': '',
        'content': ''
    }

    # 如果当前活动窗口是Word
    if info['process_name']=="winword.exe":
        try:
            # 连接到正在运行的Word实例
            word_app = win32com.client.GetActiveObject("Word.Application")
            # 获取当前活动文档
            if word_app.Documents.Count > 0:
                active_doc = word_app.ActiveDocument
                result_file_content['file_name'] = active_doc.Name
                result_file_content['file_path'] = active_doc.FullName
                result_file_content['file_type'] = "word"
                return result_file_content['file_path']
        except Exception as e:
            print(e)

    # 如果当前活动窗口是Excel
    if info['process_name']=="excel.exe":
        try:
            excel_app = win32com.client.GetActiveObject("Excel.Application")
            if excel_app.Workbooks.Count > 0:
                active_workbook = excel_app.ActiveWorkbook
                result_file_content['file_name'] = active_workbook.Name
                result_file_content['file_path'] = active_workbook.FullName
                result_file_content['file_type'] = "excel"
                result_file_content['content'] = ""
                return result_file_content['file_path']
        except Exception as e:
            print(e)

    # 如果当前活动窗口是PowerPoint
    if info['process_name']=="powerpnt.exe":
        try:
            powerpoint_app = win32com.client.GetActiveObject("PowerPoint.Application")
            if powerpoint_app.Presentations.Count > 0:
                active_presentation = powerpoint_app.ActivePresentation
                result_file_content['file_name'] = active_presentation.Name
                result_file_content['file_path'] = active_presentation.FullName
                result_file_content['file_type'] = "ppt"
                result_file_content['content'] = ""
                return result_file_content['file_path']
        except Exception as e:
            print(e)

    # 如果当前活动窗口是pycharm
    if info['process_name']=="pycharm64.exe":
        pass

    # 如果当前活动窗口是explorer.exe
    if info['process_name']=="explorer.exe":
        hwnd = win32gui.GetForegroundWindow()
        # 返回当前活动的文件夹路径
        # 使用PowerShell获取Explorer窗口的当前路径
        cmd = [
            "powershell",
            "-Command",
            "(New-Object -ComObject Shell.Application).Windows() | "
            "Where-Object { $_.HWND -eq " + str(hwnd) + " } | "
            "Select-Object -ExpandProperty LocationUrl"
        ]

        result = subprocess.run(cmd, capture_output=True, text=True, shell=True)

        if result.returncode == 0 and result.stdout.strip():
            # 处理file://协议路径
            path = result.stdout.strip()
            if path.startswith("file:///"):
                # 转换为本地路径格式
                local_path = path[8:].replace("/", "\\")
                return local_path
            return path

        # 如果上面的方法失败，尝试另一种方法
        cmd2 = [
            "powershell",
            "-Command",
            "(New-Object -ComObject Shell.Application).Windows() | "
            "Where-Object { $_.HWND -eq " + str(hwnd) + " } | "
            "Select-Object -ExpandProperty Document | "
            "Select-Object -ExpandProperty Folder | "
            "Select-Object -ExpandProperty Self | "
            "Select-Object -ExpandProperty Path"
        ]

        result2 = subprocess.run(cmd2, capture_output=True, text=True, shell=True)

        if result2.returncode == 0 and result2.stdout.strip():
            return result2.stdout.strip()

    return info['process_name']


if __name__ == "__main__":
    time.sleep(5)
    # 调用函数
    result_file_content = get_activate_path()
    print(result_file_content)
    #
    # # 访问返回值
    # file_name = result_file_content['file_name']
    # file_path = result_file_content['file_path']
    # file_type = result_file_content['file_type']
    # content = result_file_content['content']
    #
    # print(content)
    # print(file_path)
