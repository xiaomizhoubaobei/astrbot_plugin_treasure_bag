"""全局测试固件：注入 AstrBot API 桩，隔离百度认证单例状态。"""

from __future__ import annotations

import logging
import sys
import types
from pathlib import Path
from types import SimpleNamespace
from typing import ClassVar

import aiohttp
import httpx
import pytest

from .fakes import FakeAiohttpSession, FakeHttpxClient

ROOT = Path(__file__).resolve().parents[1]

COMMANDS: dict[str, object] = {}


def _install_astrbot_stub() -> None:
    if "astrbot" in sys.modules:
        return

    class AstrBotConfig(dict):
        """配置对象桩，行为与 dict 一致。"""

    class Context:
        def __init__(self, *args, **kwargs):
            pass

    class Star:
        def __init__(self, context):
            self.context = context

    class Image:
        def __init__(self, url: str = ""):
            self.url = url

    class AstrMessageEvent:
        def __init__(self, message: str = "", segments=None):
            self.message_str = message
            self.message_obj = SimpleNamespace(
                message=segments
                if segments is not None
                else [SimpleNamespace(text=message)]
            )

        def plain_result(self, text):
            return {"type": "plain", "data": text}

        def image_result(self, url):
            return {"type": "image", "data": url}

    class _Filter:
        command_registry: ClassVar[dict[str, object]] = {}

        @classmethod
        def command(cls, name, aliases=None, **kwargs):
            def decorate(func):
                func._command_name = name
                func._command_aliases = tuple(aliases or ())
                COMMANDS[name] = func
                cls.command_registry[name] = func
                return func

            return decorate

    astrbot = types.ModuleType("astrbot")
    astrbot.__path__ = []
    api = types.ModuleType("astrbot.api")
    api.__path__ = []
    core = types.ModuleType("astrbot.core")
    core.__path__ = []
    event = types.ModuleType("astrbot.api.event")
    star = types.ModuleType("astrbot.api.star")
    components = types.ModuleType("astrbot.api.message_components")

    api.logger = logging.getLogger("astrbot.test")
    api.AstrBotConfig = AstrBotConfig
    core.AstrBotConfig = AstrBotConfig
    event.filter = _Filter()
    event.AstrMessageEvent = AstrMessageEvent
    star.Context = Context
    star.Star = Star
    components.Image = Image

    sys.modules.update(
        {
            "astrbot": astrbot,
            "astrbot.api": api,
            "astrbot.core": core,
            "astrbot.api.event": event,
            "astrbot.api.star": star,
            "astrbot.api.message_components": components,
        }
    )
    # 便于 `import astrbot.api.message_components` 的点号访问
    astrbot.api = api
    api.event = event
    api.star = star
    api.message_components = components
    core.event = event


_install_astrbot_stub()

# 以包名方式挂载仓库根目录，使模块内的相对导入（..utils 等）可用。
if "treasure_bag" not in sys.modules:
    package = types.ModuleType("treasure_bag")
    package.__path__ = [str(ROOT)]
    sys.modules["treasure_bag"] = package


@pytest.fixture
def make_event():
    """返回 AstrMessageEvent 桩的工厂。"""
    from astrbot.api.event import AstrMessageEvent

    return lambda message="", segments=None: AstrMessageEvent(message, segments)


@pytest.fixture
def patch_aiohttp(monkeypatch):
    """把 aiohttp.ClientSession 替换为给定的假会话。"""

    def install(session: FakeAiohttpSession):
        monkeypatch.setattr(aiohttp, "ClientSession", lambda *args, **kwargs: session)
        return session

    return install


@pytest.fixture
def patch_httpx(monkeypatch):
    """把 httpx.AsyncClient 替换为给定的假客户端。"""

    def install(client: FakeHttpxClient):
        monkeypatch.setattr(httpx, "AsyncClient", lambda *args, **kwargs: client)
        return client

    return install


@pytest.fixture(autouse=True)
def reset_baidu_auth():
    """每个用例前后重置百度认证单例，避免状态串扰。"""
    from treasure_bag.baidu.baidu_auth import baidu_auth_manager

    original = (
        baidu_auth_manager.api_key,
        baidu_auth_manager.secret_key,
        baidu_auth_manager.access_token,
        baidu_auth_manager.token_expiry_time,
    )
    baidu_auth_manager.api_key = None
    baidu_auth_manager.secret_key = None
    baidu_auth_manager.access_token = None
    baidu_auth_manager.token_expiry_time = 0
    yield
    (
        baidu_auth_manager.api_key,
        baidu_auth_manager.secret_key,
        baidu_auth_manager.access_token,
        baidu_auth_manager.token_expiry_time,
    ) = original
