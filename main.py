from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star, register
from astrbot.api import logger
from astrbot.core import AstrBotConfig
from .hitokoto_handler import get_hitokoto
from .baidu.beauty_handler import get_beauty_score
from .baidu.baidu_auth import init_baidu_credentials
from .wangzhe_handler import get_wangzhe_info
from .handwrite_handler import get_handwritten_image
from .beauty_img_handler import get_beauty_image_url
from .chengyu_plugin import chengyu_query
from .sad_word_handler import get_sad_word 
from .xingzuo_handler import get_xingzuo_info
from .weather_handler import get_weather

@register("TreasureBag", "祁筱欣", "一个为AstrBot设计的多功能插件，包含多种实用和娱乐功能。", "0.0.2")
class HitokotoPlugin(Star):
    def __init__(self, context: Context, config: AstrBotConfig):
        super().__init__(context)
        self.config = config
        init_baidu_credentials(self.config)

    async def initialize(self):
        config = self.config
        admin = config.get("admin")
        print(admin)
        """可选择实现异步的插件初始化方法，当实例化该插件类之后会自动调用该方法。"""
        logger.info("Treasure Bag Plugin 初始化完成")
    
    @filter.command("hitokoto")
    async def hitokoto_command(self, event: AstrMessageEvent):
        """获取一条一言。"""
        yield await get_hitokoto(event)
        
    @filter.command("bdrate_beauty")
    async def recognize_face_async(self, event: AstrMessageEvent):
        """发送人像图片获取百度的颜值评分。"""
        # print(event.message_obj.raw_message) # 平台下发的原始消息在这里
        # print(event.message_obj.message) # AstrBot 解析出来的消息链内容
        yield await get_beauty_score(event)

    @filter.command("kog_info")
    async def wangzhe_command(self, event: AstrMessageEvent):
        """查询王者荣耀英雄资料。用法：王者 [英雄名称]"""
        message_segments = event.message_obj.message
        plain_text_parts = []
        if isinstance(message_segments, list):
            for segment in message_segments:
                if hasattr(segment, 'text'): # Check for .text attribute
                    plain_text_parts.append(str(segment.text)) # Convert to string
        full_text = "".join(plain_text_parts).strip()
        
        hero_name = ""
        
        command_keyword = "kog_info"
        # Check for "王者 HeroName"
        if full_text.lower().startswith(command_keyword.lower() + " "):
            hero_name = full_text[len(command_keyword) + 1:].strip()
        # Check for "/王者 HeroName"
        elif full_text.lower().startswith("/" + command_keyword.lower() + " "):
             hero_name = full_text[len(command_keyword) + 2:].strip()
        # If user types only "王者" or "/王者", hero_name remains "", which is handled by get_wangzhe_info

        yield await get_wangzhe_info(event, hero_name)

    @filter.command("handwrite")
    async def handwrite_command(self, event: AstrMessageEvent):
        """生成手写样式的图片。用法：/handwrite [内容]"""
        message_segments = event.message_obj.message
        plain_text_parts = []
        if isinstance(message_segments, list):
            for segment in message_segments:
                if hasattr(segment, 'text'): # Check for .text attribute
                    plain_text_parts.append(str(segment.text)) # Convert to string
        full_text = "".join(plain_text_parts).strip()
        
        content_to_write = ""
        command_keyword = "handwrite"
        # Check for "handwrite 内容"
        if full_text.lower().startswith(command_keyword.lower() + " "):
            content_to_write = full_text[len(command_keyword) + 1:].strip()
        # Check for "/handwrite 内容"
        elif full_text.lower().startswith("/" + command_keyword.lower() + " "):
            content_to_write = full_text[len(command_keyword) + 2:].strip()
        # If user types only "handwrite" or "/handwrite", content_to_write remains "", which is handled by get_handwritten_image

        yield event.image_result(await get_handwritten_image(event, content_to_write))

    @filter.command("beauty_img", aliases=["random_beauty", "daily_beauty", "random_beauty_image"])
    async def beauty_img_command(self, event: AstrMessageEvent):
        """获取一张随机美女图片。"""
        image_url = await get_beauty_image_url(event)
        if isinstance(image_url, str) and image_url.startswith("http"):
            yield event.image_result(image_url)
        elif isinstance(image_url, astrbot.api.message_components.MessageResult):
             yield image_url # 如果handler返回的是MessageResult（例如错误信息），直接yield
        else:
            logger.error(f"获取美女图片失败，返回内容不符合预期: {image_url}")
            yield event.plain_result("获取图片失败了，请稍后再试试吧。")
    @filter.command_group("meme")
    def erciyuan_group(self):
        pass


    @filter.command("idiom_query")
    async def chengyu_command(self, event: AstrMessageEvent):
        """成语查询插件"""
        prompt = event.message_str.split(' ')[1]
        yield await chengyu_query(event, prompt)


    @filter.command("sad-word", aliases=["伤感一言", "每日伤感", "伤感语录", "情感"])
    async def sad_word_command(self, event: AstrMessageEvent):
        """获取一条伤感语录。"""
        async for result in get_sad_word(event):
            yield result

    @filter.command("今日运势", aliases=["星座运势"])
    async def xingzuo_command(self, event: AstrMessageEvent, *, xingzuo_name: str):
        """查询星座运势。用法：/今日运势 [星座名称] 或 /星座运势 [星座名称]"""
        if not xingzuo_name:
            yield event.plain_result("请输入要查询的星座名称，例如：/今日运势 白羊座")
            return
        async for result in get_xingzuo_info(event, xingzuo_name.strip()):
            yield result

    @filter.command("weather", aliases={"天气"})
    async def weather_command(self, event: AstrMessageEvent):
        """查询天气。用法：/weather [城市名称]"""
        message_parts = event.message_str.split(' ', 1)
        if len(message_parts) < 2 or not message_parts[1].strip():
            yield event.plain_result("请输入要查询的城市名称，例如：/weather 北京")
            return
        city_name = message_parts[1].strip()
        yield await get_weather(event, city_name)

    @filter.command("treasurebag-help")
    async def help_command(self, event: AstrMessageEvent):
        """显示插件帮助信息。"""
        help_text = """
        === 百宝袋插件帮助 ===
        命令列表:
        1. /hitokoto - 获取一条一言
        2. /bdrate_beauty - 发送人像图片获取来自百度的颜值评分
        3. /成语查询 [成语] - 查询成语详细信息 (例如: /成语查询 厚德载物)
        4. /kog_info [英雄名称] - 查询王者荣耀英雄资料 (例如: /kog_info 亚瑟)
        5. /handwrite [内容] - 生成手写样式的图片 (例如: /handwrite 你好世界)
        6. /beauty_img (或 /random_beauty, /daily_beauty, /random_beauty_image) - 获取一张随机美女图片
        7. /idiom_query [成语] - 查询成语详细信息 (例如: /idiom_query 厚德载物)
        8. /sad-word (或 /伤感一言, /每日伤感, /伤感语录, /情感) - 获取一条伤感语录
        9. /今日运势 [星座名称] (或 /星座运势 [星座名称]) - 查询星座运势 (例如: /今日运势 白羊座)
        10. /alirate_beauty - 发送人像图片获取来自阿里的颜值评分
         11. /weather [城市名称] (或 /天气 [城市名称]) - 查询天气 (例如: /weather 北京)
         12. /treasurebag-help - 显示此帮助信息
        """
        yield event.plain_result(help_text)

    async def terminate(self):
        config = self.config
        admin = config.get("admin")
        print(admin)
        """可选择实现异步的插件销毁方法，当插件被卸载/停用时会调用。"""
        logger.info("Treasure Bag Plugin 已终止")
