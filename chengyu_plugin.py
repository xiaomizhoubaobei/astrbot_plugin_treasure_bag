from astrbot.api.event import  AstrMessageEvent
from astrbot.api import logger
import aiohttp
import json

async def chengyu_query(event: AstrMessageEvent, text: str):
        '''成语查询插件'''
        logger.info(f"收到成语查询请求，文本内容: {text}")
        async with aiohttp.ClientSession() as session:
            async with session.get(f'https://v.api.aa1.cn/api/api-chengyu/index.php?msg={text}') as resp:
                response_text = await resp.text()
                ret = json.loads(response_text)
        if ret['code'] == -1:
            return ret['msg']
        result = []
        desc = {
            'cycx': '查询的成语',
            'cyjs': '成语解释',
            'cycc': '成语出处',
            'cyzj': '成语造句',
            'cybx': '成语辨析',
            'cysy': '成语使用',
            'error': '查询失败返回内容'
        }
        for key, value in ret.items():
            result.append(f'{desc[key]}: {value}')
        return event.plain_result('\n'.join(result))