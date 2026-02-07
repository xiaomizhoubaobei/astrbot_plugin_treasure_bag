from astrbot.api.event import AstrMessageEvent
from astrbot.api import logger
import aiohttp
from .command_utils import extract_command_arg

# 定义API URL常量
WANGZHE_API_BASE_URL = "https://zj.v.api.aa1.cn/api/wz/"


async def wangzhe_command(event: AstrMessageEvent):
    """查询王者荣耀英雄资料。用法：/kog_info [英雄名称]"""
    hero_name = extract_command_arg(event, "kog_info")
    if not hero_name:
        yield event.plain_result("请输入要查询的英雄名称，例如：/kog_info 亚瑟")
        return
    
    api_url = f"{WANGZHE_API_BASE_URL}?msg={hero_name}"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(api_url) as resp:
                if resp.status == 200:
                    data_text = await resp.text()
                    logger.info(f"成功查询英雄 {hero_name} 的资料: {data_text[:100]}...")
                    if data_text:
                        yield event.plain_result(f"\n英雄 {hero_name} 的资料如下：\n{data_text}")
                    else:
                        yield event.plain_result(f"未能查询到英雄 {hero_name} 的资料，可能是英雄名称错误或API暂无数据。")
                else:
                    logger.error(f"请求王者荣耀API失败，英雄：{hero_name}，状态码: {resp.status}")
                    yield event.plain_result(f"抱歉，查询英雄 {hero_name} 资料失败了 (状态码: {resp.status})。")
    except Exception as e:
        logger.error(f"请求王者荣耀API时发生错误，英雄：{hero_name}: {e}")
        yield event.plain_result(f"抱歉，查询英雄 {hero_name} 资料时发生了意料之外的错误。")