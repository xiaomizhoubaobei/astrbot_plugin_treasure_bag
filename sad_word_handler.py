import httpx
from astrbot.api.event import AstrMessageEvent
from astrbot.api import logger


async def get_sad_word(event: AstrMessageEvent):
        """获取一条伤感语录。"""
        api_url = "https://v.api.aa1.cn/api/api-wenan-qg/index.php?aa1=json"
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(api_url)
                response.raise_for_status() # Raises an exception for 4XX/5XX responses
                data = response.json()
                if data and isinstance(data, list) and len(data) > 0 and "qinggan" in data[0]:
                    message = data[0]["qinggan"]
                    yield event.plain_result(message)
                else:
                    logger.error(f"SadWordHandler: Unexpected API response format: {data}")
                    yield event.plain_result("抱歉，获取伤感语录失败，请稍后再试。")
        except httpx.HTTPStatusError as e:
            logger.error(f"SadWordHandler: HTTP error occurred: {e}")
            yield event.plain_result(f"抱歉，请求API时出错: {e.response.status_code}")
        except httpx.RequestError as e:
            logger.error(f"SadWordHandler: Request error occurred: {e}")
            yield event.plain_result("抱歉，连接API失败，请检查网络或稍后再试。")
        except Exception as e:
            logger.error(f"SadWordHandler: An unexpected error occurred: {e}")
            yield event.plain_result("抱歉，发生未知错误，请稍后再试。")