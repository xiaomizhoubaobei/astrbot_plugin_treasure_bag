"""命令处理工具函数模块。"""
from astrbot.api.event import AstrMessageEvent


def extract_command_arg(event: AstrMessageEvent, command_keyword: str) -> str:
    """从消息中提取命令参数。
    
    Args:
        event: 消息事件对象
        command_keyword: 命令关键字
        
    Returns:
        提取到的参数，如果没有参数则返回空字符串
    """
    message_segments = event.message_obj.message
    plain_text_parts = []
    if isinstance(message_segments, list):
        for segment in message_segments:
            if hasattr(segment, 'text'):
                plain_text_parts.append(str(segment.text))
    full_text = "".join(plain_text_parts).strip()
    
    arg = ""
    if full_text.lower().startswith(command_keyword.lower() + " "):
        arg = full_text[len(command_keyword) + 1:].strip()
    elif full_text.lower().startswith("/" + command_keyword.lower() + " "):
        arg = full_text[len(command_keyword) + 2:].strip()
        
    return arg