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

async def get_xingzuo_info(event: AstrMessageEvent, prompt: str):
    """获取星座运势信息。"""
    api_url = f"{XINGZUO_API_BASE_URL}?msg={prompt}"
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(api_url)
            response.raise_for_status()  # Raises an exception for 4XX/5XX responses
            data = response.json()

            # Handle known error cases from API first
            if data.get("code") == -1 or data.get("msg") == "数据不存在": # Assuming this error format is still possible
                yield event.plain_result(data.get("msg", "无法查询到该星座的运势信息。"))
                return # Exit if this specific error occurs

            # New API success response format: {"code":1,"msg":"查询成功","xz":"处女",...}
            if data.get("code") == 1 and data.get("msg") == "查询成功":
                result_parts = []
                # Iterate over the root `data` object, as the relevant info is not nested under a "data" key
                for key, value in data.items(): 
                    if key in desc_map: # Use desc_map to get display names and filter relevant keys
                        result_parts.append(f"{desc_map[key]}: {value}")
                
                if result_parts:
                    yield event.plain_result("\n".join(result_parts))
                else:
                    # This case might happen if desc_map doesn't cover any keys from a successful response
                    logger.warning(f"XingzuoHandler: Successful API call but no relevant data found based on desc_map. API Response: {data}")
                    yield event.plain_result("查询成功，但未能解析出有效的运势信息。")
            # Consider if other specific error codes from the new API need handling
            # For example, if data.get("code") == 0 and data.get("msg") == "星座名不能为空":
            #     yield event.plain_result(data.get("msg", "请输入星座名称。"))
            #     return
            else: # Fallback for other error codes or unexpected structures from the new API
                logger.error(f"XingzuoHandler: Unexpected API response format or error code. API Response: {data}")
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