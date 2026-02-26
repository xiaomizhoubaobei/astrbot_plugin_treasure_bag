from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star, register
from astrbot.api import logger
from astrbot.core import AstrBotConfig
from .handlers.hitokoto_handler import get_hitokoto
from .baidu.beauty_handler import get_beauty_score
from .baidu.baidu_auth import init_baidu_credentials
from .handlers.wangzhe_handler import wangzhe_command
from .handlers.handwrite_handler import handwrite_command
from .handlers.beauty_img_handler import beauty_img_command
from .handlers.sad_word_handler import get_sad_word
from .handlers.xingzuo_handler import xingzuo_command
from .handlers.weather_handler import weather_command


@register(
    "TreasureBag",
    "祁筱欣",
    "一个为AstrBot设计的多功能插件，包含多种实用和娱乐功能。",
    "0.0.2",
)
class TreasureBagPlugin(Star):
    def __init__(self, context: Context, config: AstrBotConfig):
        super().__init__(context)
        self.config = config
        init_baidu_credentials(self.config)

    async def initialize(self):
        """插件初始化方法，当实例化该插件类之后会自动调用该方法。"""
        logger.info("Treasure Bag Plugin 初始化完成")

    @filter.command("hitokoto")
    async def hitokoto_command(self, event: AstrMessageEvent):
        """获取一条一言。"""
        yield await get_hitokoto(event)

    @filter.command("bdrate_beauty")
    async def bdrate_beauty_command(self, event: AstrMessageEvent):
        """发送人像图片获取百度的颜值评分。"""
        yield await get_beauty_score(event)

    @filter.command("kog_info")
    async def kog_info_command(self, event: AstrMessageEvent):
        """查询王者荣耀英雄资料。"""
        async for result in wangzhe_command(event):
            yield result

    @filter.command("handwrite")
    async def handwrite_command(self, event: AstrMessageEvent):
        """生成手写样式的图片。"""
        async for result in handwrite_command(event):
            yield result

    @filter.command(
        "beauty_img", aliases=["random_beauty", "daily_beauty", "random_beauty_image"]
    )
    async def beauty_img_command(self, event: AstrMessageEvent):
        """获取一张随机美女图片。"""
        async for result in beauty_img_command(event):
            yield result

    @filter.command("sad-word", aliases=["伤感一言", "每日伤感", "伤感语录", "情感"])
    async def sad_word_command(self, event: AstrMessageEvent):
        """获取一条伤感语录。"""
        async for result in get_sad_word(event):
            yield result

    @filter.command("今日运势", aliases=["星座运势"])
    async def xingzuo_command(self, event: AstrMessageEvent, *, xingzuo_name: str):
        """查询星座运势。"""
        async for result in xingzuo_command(event, xingzuo_name):
            yield result

    @filter.command("weather", aliases=["天气"])
    async def weather_command(self, event: AstrMessageEvent):
        """查询天气。"""
        async for result in weather_command(event):
            yield result

    @filter.command("treasurebag-help")
    async def help_command(self, event: AstrMessageEvent):
        """显示插件帮助信息。"""
        help_text = """
        === 百宝袋插件帮助 ===
        命令列表:
        1. /hitokoto - 获取一条一言
        2. /bdrate_beauty - 发送人像图片获取来自百度的颜值评分
        3. /kog_info [英雄名称] - 查询王者荣耀英雄资料 (例如: /kog_info 亚瑟)
        4. /handwrite [内容] - 生成手写样式的图片 (例如: /handwrite 你好世界)
        5. /beauty_img (或 /random_beauty, /daily_beauty, /random_beauty_image) - 获取一张随机美女图片
        6. /sad-word (或 /伤感一言, /每日伤感, /伤感语录, /情感) - 获取一条伤感语录
        7. /今日运势 [星座名称] (或 /星座运势 [星座名称]) - 查询星座运势 (例如: /今日运势 白羊座)
        8. /weather [城市名称] (或 /天气 [城市名称]) - 查询天气 (例如: /weather 北京)
        9. /treasurebag-help - 显示此帮助信息
        """
        yield event.plain_result(help_text)

    async def terminate(self):
        """插件销毁方法，当插件被卸载/停用时会调用。"""
        logger.info("Treasure Bag Plugin 已终止")
