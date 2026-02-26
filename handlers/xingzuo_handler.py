import httpx
from astrbot.api.event import AstrMessageEvent
from astrbot.api import logger

# 定义API URL常量
XINGZUO_API_BASE_URL = "https://v.api.aa1.cn/api/xingzuo/"

desc_map = {
    "xz": "星座",
    "grfw": "贵人方位",
    "grxz": "贵人星座",
    "xysz": "幸运数字",
    "xyys": "幸运颜色",
    "aqys": "爱情运势",
    "cfys": "财富运势",
    "syys": "事业运势",
    "ztys": "整体运势",
    "ts": "提示",
}


async def xingzuo_command(event: AstrMessageEvent, xingzuo_name: str = None):
    """查询星座运势。"""
    if not xingzuo_name:
        yield event.plain_result("请输入要查询的星座名称，例如：/今日运势 白羊座")
        return
    
    prompt = xingzuo_name.strip()
    api_url = f"{XINGZUO_API_BASE_URL}?msg={prompt}"
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(api_url)
            response.raise_for_status()
            data = response.json()

            if data.get("code") == -1 or data.get("msg") == "数据不存在":
                yield event.plain_result(data.get("msg", "无法查询到该星座的运势信息。"))
                return

            if data.get("code") == 1 and data.get("msg") == "查询成功":
                result_parts = []
                for key, value in data.items():
                    if key in desc_map:
                        result_parts.append(f"{desc_map[key]}: {value}")
                
                if result_parts:
                    yield event.plain_result("\n".join(result_parts))
                else:
                    logger.warning(f"XingzuoHandler: Successful API call but no relevant data found. API Response: {data}")
                    yield event.plain_result("查询成功，但未能解析出有效的运势信息。")
            else:
                logger.error(f"XingzuoHandler: Unexpected API response format. API Response: {data}")
                yield event.plain_result("抱歉，获取星座运势失败，API响应未知或包含错误。")

    except httpx.HTTPStatusError as e:
        logger.error(f"XingzuoHandler: HTTP error occurred: {e}")
        yield event.plain_result(f"抱歉，请求API时出错: {e.response.status_code}")
    except httpx.RequestError as e:
        logger.error(f"XingzuoHandler: Request error occurred: {e}")
        yield event.plain_result("抱歉，连接API失败，请检查网络或稍后再试。")
    except Exception as e:
        logger.error(f"XingzuoHandler: An unexpected error occurred: {e}")
        yield event.plain_result("抱歉，发生未知错误，请稍后再试。")