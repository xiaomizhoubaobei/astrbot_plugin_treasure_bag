from datetime import datetime
import aiohttp
from astrbot.api import logger, AstrBotConfig # 假设 logger 可访问或在其他地方定义（如果不是 astrbot.api 的一部分）

# 百度 API 凭证和令牌缓存
BAIDU_API_KEY = None
BAIDU_SECRET_KEY = None
BAIDU_ACCESS_TOKEN = None
BAIDU_TOKEN_EXPIRY_TIME = 0  # 令牌过期的Unix时间戳

def init_baidu_credentials(config: AstrBotConfig):
    """从插件配置中初始化百度API凭证。"""
    global BAIDU_API_KEY, BAIDU_SECRET_KEY
    BAIDU_API_KEY = config.get("baidu_api_key")
    BAIDU_SECRET_KEY = config.get("baidu_secret_key")
    if not BAIDU_API_KEY or not BAIDU_SECRET_KEY:
        logger.warning("百度API Key或Secret Key未在插件配置中完全配置。请检查插件配置。")
    else:
        logger.info(f"百度API凭证已从插件配置加载。API Key: {BAIDU_API_KEY[:4]}...{BAIDU_API_KEY[-4:]}, Secret Key: {BAIDU_SECRET_KEY[:4]}...{BAIDU_SECRET_KEY[-4:]}")

async def get_baidu_access_token():
    """获取百度API的access_token, 并缓存。"""
    global BAIDU_ACCESS_TOKEN, BAIDU_TOKEN_EXPIRY_TIME

    current_time = datetime.now().timestamp()
    # 检查令牌是否存在且尚未过期（例如，如果剩余时间少于1小时则刷新）
    if BAIDU_ACCESS_TOKEN and current_time < (BAIDU_TOKEN_EXPIRY_TIME - 3600):
        return BAIDU_ACCESS_TOKEN

    if not BAIDU_API_KEY or not BAIDU_SECRET_KEY:
        logger.error("百度API Key或Secret Key未配置。")
        raise Exception("百度API凭证未配置。")

    token_url = "https://aip.baidubce.com/oauth/2.0/token"
    params = {
        "grant_type": "client_credentials",
        "client_id": BAIDU_API_KEY,
        "client_secret": BAIDU_SECRET_KEY
    }
    logger.info(f"正在请求百度access_token, 参数: grant_type=client_credentials, client_id={BAIDU_API_KEY[:4]}..., client_secret={BAIDU_SECRET_KEY[:4]}...")
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(token_url, params=params) as resp:
                if resp.status == 200:
                    token_data = await resp.json()
                    if "access_token" in token_data:
                        BAIDU_ACCESS_TOKEN = token_data["access_token"]
                        # expires_in 以秒为单位，通常为 2592000 秒（30天）
                        BAIDU_TOKEN_EXPIRY_TIME = current_time + token_data.get("expires_in", 2592000)
                        logger.info(f"成功获取百度 access_token，有效期至: {datetime.fromtimestamp(BAIDU_TOKEN_EXPIRY_TIME)}")
                        return BAIDU_ACCESS_TOKEN
                    else:
                        error_msg = token_data.get('error_description', token_data.get('error', '未知错误'))
                        logger.error(f"获取百度 access_token 失败: {error_msg}")
                        raise Exception(f"获取百度 access_token 失败: {error_msg}")
                else:
                    error_text = await resp.text()
                    logger.error(f"请求百度 access_token API 失败，状态码: {resp.status}, 响应: {error_text}")
                    raise Exception(f"请求百度 access_token API 失败，状态码: {resp.status}")
    except aiohttp.ClientError as e:
        logger.error(f"连接百度认证服务时发生错误: {e}")
        raise Exception(f"连接百度认证服务时发生错误: {e}")