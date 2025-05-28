from astrbot.api.event import AstrMessageEvent
from astrbot.api import logger
import aiohttp

async def get_hitokoto(event: AstrMessageEvent):
    """获取一条一言。"""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get("https://v1.hitokoto.cn/") as resp:
                if resp.status == 200:
                    data = await resp.json()
                    hitokoto_text = data.get("hitokoto", "")
                    from_who = data.get("from_who", "")
                    from_source = data.get("from", "")
                    logger.info(f"成功获取一言: {hitokoto_text} —— {from_who if from_who else ''} 《{from_source}》")
                    if from_who:
                        return event.plain_result(f"\n{hitokoto_text} —— {from_who} 《{from_source}》")
                    else:
                        return event.plain_result(f"\n{hitokoto_text} —— 《{from_source}》")
                else:
                    logger.error(f"请求一言 API 失败，状态码: {resp.status}")
                    return event.plain_result("抱歉，获取一言失败了。")
    except Exception as e:
        logger.error(f"请求一言 API 时发生错误: {e}")
        return event.plain_result("抱歉，获取一言时发生了意料之外的错误。")