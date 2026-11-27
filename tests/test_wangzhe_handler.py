"""handlers.wangzhe_handler 单元测试。"""

import aiohttp
from treasure_bag.handlers.wangzhe_handler import (
    WANGZHE_API_BASE_URL,
    wangzhe_command,
)

from tests.fakes import FakeAiohttpSession, FakeResponse


async def collect(event):
    return [item async for item in wangzhe_command(event)]


def session_for(hero_name, **kwargs):
    url = f"{WANGZHE_API_BASE_URL}?msg={hero_name}"
    return FakeAiohttpSession(get={url: FakeResponse(**kwargs)})


async def test_wangzhe_empty_input(make_event):
    results = await collect(make_event("/kog_info"))
    assert results[0]["type"] == "plain"
    assert "请输入要查询的英雄名称" in results[0]["data"]


async def test_wangzhe_success(make_event, patch_aiohttp):
    patch_aiohttp(session_for("亚瑟", text_data="亚瑟：一个强大的战士"))
    results = await collect(make_event("/kog_info 亚瑟"))
    assert results[0]["type"] == "plain"
    assert "英雄 亚瑟 的资料如下" in results[0]["data"]
    assert "亚瑟：一个强大的战士" in results[0]["data"]


async def test_wangzhe_empty_response(make_event, patch_aiohttp):
    patch_aiohttp(session_for("未知", text_data=""))
    results = await collect(make_event("/kog_info 未知"))
    assert "未能查询到英雄" in results[0]["data"]


async def test_wangzhe_http_error(make_event, patch_aiohttp):
    patch_aiohttp(session_for("亚瑟", status=404))
    results = await collect(make_event("/kog_info 亚瑟"))
    assert "状态码: 404" in results[0]["data"]


async def test_wangzhe_network_error(make_event, patch_aiohttp):
    url = f"{WANGZHE_API_BASE_URL}?msg=亚瑟"
    patch_aiohttp(FakeAiohttpSession(get={url: aiohttp.ClientError("boom")}))
    results = await collect(make_event("/kog_info 亚瑟"))
    assert "意料之外的错误" in results[0]["data"]
