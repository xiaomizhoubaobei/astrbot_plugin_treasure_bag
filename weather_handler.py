from astrbot.api.event import AstrMessageEvent
from astrbot.api import logger
import aiohttp
import json

async def get_weather(event: AstrMessageEvent, city: str):
    """获取天气信息。"""
    try:
        if not city:
            return event.plain_result("请告诉我您想查询天气的城市，例如：天气 北京")

        url = "https://api.lolimi.cn/API/weather/api.php"
        params = {
            'city': city,
            'type': 'json',
        }
        logger.info(f"请求天气 API,URL: {url}, 参数: {params}")
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params) as resp:
                if resp.status == 200:
                    try:
                        xydata = await resp.json()
                    except json.JSONDecodeError as e:
                        logger.error(f"解析天气 API 返回的 JSON 数据失败: {e}")
                        return event.plain_result("抱歉，解析天气数据时出错了。")
                    if xydata.get("code") == 1:
                        data = xydata.get("data")
                        weather = data.get("weather")
                        current = data.get("current")
                        humidity = current.get("humidity")
                        wind = current.get("wind")
                        wind_speed = current.get("windSpeed")
                        visibility = current.get("visibility")
                        temp = current.get("temp")
                        fahrenheit = current.get("fahrenheit")
                        air = current.get("air")
                        air_pm25 = current.get("air_pm25")
                        living = data.get("living")
                        living_tips = "\n".join([f"{item['name']}: {item['tips']}" for item in living])

                        response_text = (
                            f"城市: {city}\n"
                            f"天气: {weather}\n"
                            f"温度: {temp}°C ({fahrenheit}°F)\n"
                            f"湿度: {humidity}%\n"
                            f"风力: {wind} {wind_speed}\n"
                            f"能见度: {visibility}\n"
                            f"空气质量: {air} (PM2.5: {air_pm25})\n"
                            f"\n生活指数:\n{living_tips}"
                        )

                        logger.info(f"成功获取天气信息: {city}")
                        return event.plain_result(response_text)
                    else:
                        error_text = xydata.get("text", "未知错误")
                        logger.error(f"请求天气 API 失败: {error_text}")
                        return event.plain_result(f"抱歉，获取天气失败了: {error_text}")
                else:
                    logger.error(f"请求天气 API 失败，状态码: {resp.status}")
                    return event.plain_result("抱歉，获取天气失败了。")
    except Exception as e:
        logger.error(f"请求天气 API 时发生错误: {e}")
        return event.plain_result("抱歉，获取天气时发生了意料之外的错误。")