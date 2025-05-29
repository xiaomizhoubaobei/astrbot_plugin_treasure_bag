from astrbot.api import logger
from astrbot.api.event import AstrMessageEvent


async def parse_target(event: AstrMessageEvent):
    """解析@目标或用户名"""
    for comp in event.message_obj.message:
        if isinstance(comp, At) and event.get_self_id() != str(comp.qq):
            return str(comp.qq)
    return None


async def get_meme_image(event):
    """根据QQ号和类型生成表情包图片。"""
    qq = await parse_target(event)
    if not qq:
        return event.plain_result("请@目标或输入用户名。")
    logger.info(event)
    url = "https://api.lolimi.cn/API/preview/api.php?action=create_meme&qq=3498949583&type=5"
    return url
