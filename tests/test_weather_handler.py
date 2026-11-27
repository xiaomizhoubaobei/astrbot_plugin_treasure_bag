"""handlers.weather_handler 单元测试。"""

import json

import aiohttp
from treasure_bag.handlers.weather_handler import weather_command

from tests.fakes import FakeAiohttpSession, FakeResponse

URL = "https://api.lolimi.cn/API/weather/api.php"


async def collect(event):
    return [item async for item in weather_command(event)]


def weather_payload():
    return {
        "code": 1,
        "data": {
            "weather": "晴",
            "current": {
                "temp": 26,
                "fahrenheit": 79,
                "humidity": 60,
                "wind": "东南风",
                "windSpeed": "3级",
                "visibility": "10km",
                "air": "优",
                "air_pm25": 12,
            },
            "living": [
                {"name": "穿衣", "tips": "轻薄透气"},
                {"name": "出行", "tips": "适合外出"},
            ],
        },
    }


async def test_weather_empty_input(make_event):
    results = await collect(make_event("/weather"))
    assert "请输入要查询的城市名称" in results[0]["data"]


async def test_weather_success(make_event, patch_aiohttp):
    patch_aiohttp(
        FakeAiohttpSession(get={URL: FakeResponse(json_data=weather_payload())})
    )
    results = await collect(make_event("/weather 北京"))
    text = results[0]["data"]
    assert results[0]["type"] == "plain"
    assert "城市: 北京" in text
    assert "天气: 晴" in text
    assert "温度: 26°C (79°F)" in text
    assert "穿衣: 轻薄透气" in text


async def test_weather_api_error(make_event, patch_aiohttp):
    patch_aiohttp(
        FakeAiohttpSession(
            get={URL: FakeResponse(json_data={"code": 0, "text": "城市不存在"})}
        )
    )
    results = await collect(make_event("/weather 火星"))
    assert "获取天气失败了: 城市不存在" in results[0]["data"]


async def test_weather_invalid_json(make_event, patch_aiohttp):
    patch_aiohttp(
        FakeAiohttpSession(
            get={URL: FakeResponse(json_error=json.JSONDecodeError("bad", "x", 0))}
        )
    )
    results = await collect(make_event("/weather 北京"))
    assert "解析天气数据时出错了" in results[0]["data"]


async def test_weather_http_error(make_event, patch_aiohttp):
    patch_aiohttp(FakeAiohttpSession(get={URL: FakeResponse(status=500)}))
    results = await collect(make_event("/weather 北京"))
    assert results[0]["data"] == "抱歉，获取天气失败了。"


async def test_weather_network_error(make_event, patch_aiohttp):
    patch_aiohttp(FakeAiohttpSession(get={URL: aiohttp.ClientError("boom")}))
    results = await collect(make_event("/weather 北京"))
    assert "意料之外的错误" in results[0]["data"]
