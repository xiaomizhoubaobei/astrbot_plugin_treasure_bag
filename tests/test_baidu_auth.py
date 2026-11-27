"""baidu.baidu_auth 单元测试。"""

import time

import aiohttp
import pytest
from treasure_bag.baidu.baidu_auth import (
    BaiduAuthManager,
    baidu_auth_manager,
    get_baidu_access_token,
    init_baidu_credentials,
)

from tests.fakes import FakeAiohttpSession, FakeResponse

TOKEN_URL = "https://aip.baidubce.com/oauth/2.0/token"
CONFIG = {"baidu_api_key": "abcd12345678", "baidu_secret_key": "wxyz87654321"}


def make_manager():
    manager = BaiduAuthManager()
    manager.init_credentials(CONFIG)
    return manager


async def test_init_credentials_loads_config():
    manager = make_manager()
    assert manager.api_key == CONFIG["baidu_api_key"]
    assert manager.secret_key == CONFIG["baidu_secret_key"]


async def test_get_access_token_fetches_and_caches(patch_aiohttp):
    manager = make_manager()
    session = patch_aiohttp(
        FakeAiohttpSession(
            post={
                TOKEN_URL: FakeResponse(
                    json_data={"access_token": "token-1", "expires_in": 2592000}
                )
            }
        )
    )
    assert await manager.get_access_token() == "token-1"
    assert await manager.get_access_token() == "token-1"
    # 仅发出一次网络请求，第二次命中缓存
    assert len(session.calls) == 1


async def test_get_access_token_refreshes_when_near_expiry(patch_aiohttp):
    manager = make_manager()
    manager.access_token = "old-token"
    manager.token_expiry_time = time.time() + 1800  # 剩余不足 1 小时
    patch_aiohttp(
        FakeAiohttpSession(
            post={
                TOKEN_URL: FakeResponse(
                    json_data={"access_token": "new-token", "expires_in": 7200}
                )
            }
        )
    )
    assert await manager.get_access_token() == "new-token"


async def test_get_access_token_without_credentials_raises():
    manager = BaiduAuthManager()
    with pytest.raises(Exception, match="凭证未配置"):
        await manager.get_access_token()


async def test_get_access_token_api_error(patch_aiohttp):
    manager = make_manager()
    patch_aiohttp(
        FakeAiohttpSession(
            post={
                TOKEN_URL: FakeResponse(
                    json_data={
                        "error": "invalid_client",
                        "error_description": "凭证无效",
                    }
                )
            }
        )
    )
    with pytest.raises(Exception, match="凭证无效"):
        await manager.get_access_token()


async def test_get_access_token_http_error(patch_aiohttp):
    manager = make_manager()
    patch_aiohttp(FakeAiohttpSession(post={TOKEN_URL: FakeResponse(status=401)}))
    with pytest.raises(Exception, match="状态码: 401"):
        await manager.get_access_token()


async def test_get_access_token_network_error(patch_aiohttp):
    manager = make_manager()
    patch_aiohttp(
        FakeAiohttpSession(post={TOKEN_URL: aiohttp.ClientError("connection lost")})
    )
    with pytest.raises(Exception, match="连接百度认证服务时发生错误"):
        await manager.get_access_token()


async def test_module_level_helpers_use_global_manager():
    init_baidu_credentials(CONFIG)
    assert baidu_auth_manager.api_key == CONFIG["baidu_api_key"]
    baidu_auth_manager.access_token = "cached"
    baidu_auth_manager.token_expiry_time = time.time() + 7200
    assert await get_baidu_access_token() == "cached"
