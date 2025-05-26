from astrbot.api.event import AstrMessageEvent
from astrbot.api import logger
from urllib.parse import quote

async def get_handwritten_image(event: AstrMessageEvent, text: str):
    logger.info(f"收到手写图片生成请求，文本内容: {text}")
    """根据用户提供的文本生成手写样式的图片。"""
    if not text:
        logger.warning("手写图片生成请求文本为空")
        return event.plain_result("请输入要生成手写图片的文字内容，例如：handwrite 你好呀")

    # 确保文本已进行 URL 编码
    encoded_text = quote(text)
    api_url = f"https://zj.v.api.aa1.cn/api/zuoye/?msg={encoded_text}"

    logger.info(f"手写图片 API URL: {api_url}")
    # 返回图片 URL 字符串
    return api_url