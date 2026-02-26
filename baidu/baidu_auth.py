from datetime import datetime
import aiohttp
import asyncio
from astrbot.api import logger, AstrBotConfig


class BaiduAuthManager:
    """百度API认证管理器，负责处理百度API的认证和令牌管理。"""

    def __init__(self):
        self.api_key = None
        self.secret_key = None
        self.access_token = None
        self.token_expiry_time = 0  # 令牌过期的Unix时间戳
        self._lock = asyncio.Lock()  # 用于并发控制的锁

    def init_credentials(self, config: AstrBotConfig):
        """从插件配置中初始化百度API凭证。"""
        self.api_key = config.get("baidu_api_key")
        self.secret_key = config.get("baidu_secret_key")
        if not self.api_key or not self.secret_key:
            logger.warning(
                "百度API Key或Secret Key未在插件配置中完全配置。请检查插件配置。"
            )
        else:
            logger.info(
                f"百度API凭证已从插件配置加载。API Key: {self.api_key[:4]}...{self.api_key[-4:]}, Secret Key: {self.secret_key[:4]}...{self.secret_key[-4:]}"
            )

    async def get_access_token(self):
        """获取百度API的access_token, 并缓存。使用锁确保并发安全。"""
        async with self._lock:  # 使用锁确保在并发场景下只有一个请求获取新token
            current_time = datetime.now().timestamp()
            # 检查令牌是否存在且尚未过期（例如，如果剩余时间少于1小时则刷新）
            if self.access_token and current_time < (self.token_expiry_time - 3600):
                return self.access_token

            if not self.api_key or not self.secret_key:
                logger.error("百度API Key或Secret Key未配置。")
                raise Exception("百度API凭证未配置。")

            token_url = "https://aip.baidubce.com/oauth/2.0/token"
            params = {
                "grant_type": "client_credentials",
                "client_id": self.api_key,
                "client_secret": self.secret_key,
            }
            logger.info(
                f"正在请求百度access_token, 参数: grant_type=client_credentials, client_id={self.api_key[:4]}..., client_secret={self.secret_key[:4]}..."
            )
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.post(token_url, params=params) as resp:
                        if resp.status == 200:
                            token_data = await resp.json()
                            if "access_token" in token_data:
                                self.access_token = token_data["access_token"]
                                # expires_in 以秒为单位，通常为 2592000 秒（30天）
                                self.token_expiry_time = current_time + token_data.get(
                                    "expires_in", 2592000
                                )
                                logger.info(
                                    f"成功获取百度 access_token，有效期至: {datetime.fromtimestamp(self.token_expiry_time)}"
                                )
                                return self.access_token
                            else:
                                error_msg = token_data.get(
                                    "error_description",
                                    token_data.get("error", "未知错误"),
                                )
                                logger.error(f"获取百度 access_token 失败: {error_msg}")
                                raise Exception(
                                    f"获取百度 access_token 失败: {error_msg}"
                                )
                        else:
                            error_text = await resp.text()
                            logger.error(
                                f"请求百度 access_token API 失败，状态码: {resp.status}, 响应: {error_text}"
                            )
                            raise Exception(
                                f"请求百度 access_token API 失败，状态码: {resp.status}"
                            )
            except aiohttp.ClientError as e:
                logger.error(f"连接百度认证服务时发生错误: {e}")
                raise Exception(f"连接百度认证服务时发生错误: {e}")


# 创建一个全局实例，供其他模块使用
baidu_auth_manager = BaiduAuthManager()


# 为了向后兼容，提供与原全局函数相同的接口
def init_baidu_credentials(config: AstrBotConfig):
    """从插件配置中初始化百度API凭证。"""
    baidu_auth_manager.init_credentials(config)


async def get_baidu_access_token():
    """获取百度API的access_token, 并缓存。"""
    return await baidu_auth_manager.get_access_token()
