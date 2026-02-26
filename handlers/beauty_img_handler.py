import aiohttp
from astrbot.api.event import AstrMessageEvent
from astrbot.api import logger

# 美女图片API地址
BEAUTY_IMAGE_API_URL = "https://v.api.aa1.cn/api/pc-girl_bz/index.php?wpon=url"


async def _get_beauty_image_url() -> str | None:
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
                    image_path = (await response.text()).strip()
                    if image_path.startswith("//"):
                        full_url = "https:" + image_path
                    elif not image_path.startswith("http"):
                        full_url = "https://" + image_path
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


async def beauty_img_command(event: AstrMessageEvent):
    """获取一张随机美女图片。"""
    try:
        image_url = await _get_beauty_image_url()
        if image_url and image_url.startswith("http"):
            yield event.image_result(image_url)
        else:
            logger.error(f"获取美女图片失败，返回的URL无效: {image_url}")
            yield event.plain_result("获取图片失败了，请稍后再试试吧。")
    except Exception as e:
        logger.error(f"获取美女图片时发生错误: {e}")
        yield event.plain_result("获取图片时发生网络错误，请稍后再试。")
