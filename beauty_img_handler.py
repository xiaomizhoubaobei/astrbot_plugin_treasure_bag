from astrbot.api.event import AstrMessageEvent
from astrbot.api import logger
import aiohttp

# 美女图片API地址
BEAUTY_IMAGE_API_URL = "https://v.api.aa1.cn/api/pc-girl_bz/index.php?wpon=url"

async def get_beauty_image_url() -> str | None:
    """获取随机美女图片 URL。
    
    Returns:
        str: 成功时返回图片URL
        None: 获取失败时返回None
    """
    api_url = BEAUTY_IMAGE_API_URL
    logger.info(f"请求随机美女图片 API: {BEAUTY_IMAGE_API_URL}")
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
                    return None
    except Exception as e:
        logger.error(f"请求 API 时发生错误: {e}")
        return None