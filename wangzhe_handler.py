from astrbot.api.event import AstrMessageEvent
from astrbot.api import logger
import aiohttp

async def get_wangzhe_info(event: AstrMessageEvent, hero_name: str):
    """查询王者荣耀英雄资料。"""
    if not hero_name:
        return event.plain_result("请输入要查询的英雄名称，例如：王者 亚瑟")

    api_url = f"https://zj.v.api.aa1.cn/api/wz/?msg={hero_name}"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(api_url) as resp:
                if resp.status == 200:
                    # 假设API直接返回文本格式的英雄资料
                    data_text = await resp.text()
                    logger.info(f"成功查询英雄 {hero_name} 的资料: {data_text[:100]}...") # 日志中记录部分结果
                    if data_text:
                        return event.plain_result(f"\n英雄 {hero_name} 的资料如下：\n{data_text}")
                    else:
                        return event.plain_result(f"未能查询到英雄 {hero_name} 的资料，可能是英雄名称错误或API暂无数据。")
                else:
                    logger.error(f"请求王者荣耀API失败，英雄：{hero_name}，状态码: {resp.status}")
                    return event.plain_result(f"抱歉，查询英雄 {hero_name} 资料失败了 (状态码: {resp.status})。")
    except Exception as e:
        logger.error(f"请求王者荣耀API时发生错误，英雄：{hero_name}: {e}")
        return event.plain_result(f"抱歉，查询英雄 {hero_name} 资料时发生了意料之外的错误。")