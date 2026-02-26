from astrbot.api.event import AstrMessageEvent
from astrbot.api import logger
from urllib.parse import quote
from .command_utils import extract_command_arg


async def handwrite_command(event: AstrMessageEvent):
    """生成手写样式的图片。用法：/handwrite [内容]"""
    content_to_write = extract_command_arg(event, "handwrite")

    logger.info(f"收到手写图片生成请求，文本内容: {content_to_write}")
    if not content_to_write:
        logger.warning("手写图片生成请求文本为空")
        yield event.plain_result(
            "请输入要转换成手写体的文本内容，例如：/handwrite 你好呀"
        )
        return

    # 确保文本已进行 URL 编码
    encoded_text = quote(content_to_write)
    api_url = f"https://zj.v.api.aa1.cn/api/zuoye/?msg={encoded_text}"

    logger.info(f"手写图片 API URL: {api_url}")
    yield event.image_result(api_url)
