from astrbot.api.event import AstrMessageEvent
from astrbot.api import logger
import aiohttp

async def get_beauty_image_url(event: AstrMessageEvent):
    """获取随机美女图片 URL。"""
    api_url = "https://v.api.aa1.cn/api/pc-girl_bz/index.php?wpon=url"
    logger.info(f"请求随机美女图片 API: {api_url}")
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(api_url) as response:
                if response.status == 200:
                    image_path = (await response.text()).strip() # 去除首尾空格
                    # API 返回的 URL 可能不包含协议头，或者包含的是 //
                    if image_path.startswith("//"):
                        full_url = "https:" + image_path
                    elif not image_path.startswith("http"):
                        full_url = "https://" + image_path # 兜底处理，如果API行为改变
                    else:
                        full_url = image_path
                    logger.info(f"获取到图片 URL: {full_url}")
                    return full_url
                else:
                    logger.error(f"请求 API 失败，状态码: {response.status}")
                    return event.plain_result("获取图片失败，请稍后再试。")
    except Exception as e:
        logger.error(f"请求 API 时发生错误: {e}")
        return event.plain_result("获取图片时发生网络错误，请稍后再试。")