#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import requests
import json
from dotenv import load_dotenv
import random
import os

load_dotenv()  # 默认会加载根目录下的.env文件

''' official website  https://www.qweather.com '''
'''      dev website  https://dev.qweather.com'''
mykey = '&key=' + os.getenv("QWEATHER_API_KEY") # EDIT HERE!  APIKEY

url_api_weather = 'https://devapi.qweather.com/v7/weather/'
url_api_geo = 'https://geoapi.qweather.com/v2/city/'
url_api_rain = 'https://devapi.qweather.com/v7/minutely/5m'
url_api_air = 'https://devapi.qweather.com/v7/air/now'

def get(api_type, city_id):
    url = url_api_weather + api_type + '?location=' + city_id + mykey
    return requests.get(url).json()

def rain(lat, lon):
    url = url_api_rain  + '?location=' + lon + ',' + lat + mykey
    return requests.get(url).json()

def air(city_id):
    url = url_api_air + '?location=' + city_id + mykey
    return requests.get(url).json()

def get_city(city_kw):
    url_v2 = url_api_geo + 'lookup?location=' + city_kw + mykey
    city = requests.get(url_v2).json()['location'][0]

    city_id = city['id']
    district_name = city['name']
    city_name = city['adm2']
    province_name = city['adm1']
    country_name = city['country']
    lat = city['lat']
    lon = city['lon']

    return city_id, district_name, city_name, province_name, country_name, lat, lon

# 删除原来的 now(), daily(), hourly() 函数，因为它们依赖未定义的全局变量

def weather_message(city_input):
    city_idname = get_city(city_input)

    city_id = city_idname[0]

    get_now = get('now', city_id)
    get_daily = get('3d', city_id) # 3d/7d/10d/15d
    get_hourly = get('24h', city_id) # 24h/72h/168h
    air_now = air(city_id)['now']

    #print(json.dumps(get_now, sort_keys=True, indent=4))
    if city_idname[2] == city_idname[1]:
        city_message = (city_idname[3], str(city_idname[2]) + '市')
    else:
        city_message = (city_idname[3], str(city_idname[2]) + '市', str(city_idname[1]) + '区')

    now_weather_message = ('当前天气：', get_now['now']['text'], get_now['now']['temp'], '°C', '体感温度', get_now['now']['feelsLike'], '°C')
    air_quality = ('空气质量指数：', air_now['aqi'])
    today_weather_message = ('今日天气：', get_daily['daily'][0]['textDay'], get_daily['daily'][0]['tempMin'], '-', get_daily['daily'][0]['tempMax'], '°C')

    nHoursLater = 1 # future weather hourly
    nHoursLater_weather_message = (nHoursLater, '小时后天气：', get_hourly['hourly'][1]['text'], get_hourly['hourly'][1]['temp'], '°C')

    nDaysLater = 1 # future weather daily
    nDaysLater_weather_message = (nDaysLater, '天后天气：', get_daily['daily'][nDaysLater]['textDay'], get_daily['daily'][nDaysLater]['tempMin'], '-', get_daily['daily'][nDaysLater]['tempMax'], '°C')

    return city_message, now_weather_message, air_quality, today_weather_message, nHoursLater_weather_message, nDaysLater_weather_message

if __name__ == '__main__':
    print(weather_message('淄博'))
