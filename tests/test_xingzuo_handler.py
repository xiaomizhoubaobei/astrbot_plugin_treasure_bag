"""handlers.xingzuo_handler 单元测试。"""

import httpx
from treasure_bag.handlers.xingzuo_handler import (
    XINGZUO_API_BASE_URL,
    xingzuo_command,
)

from tests.fakes import FakeHttpxClient, FakeHttpxResponse


async def collect(name, make_event):
    return [item async for item in xingzuo_command(make_event("/今日运势"), name)]


def url_for(name):
    return f"{XINGZUO_API_BASE_URL}?msg={name}"


async def test_xingzuo_empty_name(make_event):
    results = await collect(None, make_event)
    assert results[0]["type"] == "plain"
    assert "请输入要查询的星座名称" in results[0]["data"]


async def test_xingzuo_success(patch_httpx, make_event):
    name = "白羊座"
    patch_httpx(
        FakeHttpxClient(
            get={
                url_for(name): FakeHttpxResponse(
                    json_data={
                        "code": 1,
                        "msg": "查询成功",
                        "xz": "白羊座",
                        "aqys": "桃花朵朵开",
                        "unknown": "忽略我",
                    }
                )
            }
        )
    )
    results = await collect(name, make_event)
    assert results[0]["type"] == "plain"
    assert "星座: 白羊座" in results[0]["data"]
    assert "爱情运势: 桃花朵朵开" in results[0]["data"]
    assert "忽略我" not in results[0]["data"]


async def test_xingzuo_data_not_found(patch_httpx, make_event):
    name = "不存在座"
    patch_httpx(
        FakeHttpxClient(
            get={
                url_for(name): FakeHttpxResponse(
                    json_data={"code": -1, "msg": "数据不存在"}
                )
            }
        )
    )
    results = await collect(name, make_event)
    assert results[0]["data"] == "数据不存在"


async def test_xingzuo_success_but_no_mapped_fields(patch_httpx, make_event):
    name = "奇怪座"
    patch_httpx(
        FakeHttpxClient(
            get={
                url_for(name): FakeHttpxResponse(
                    json_data={"code": 1, "msg": "查询成功"}
                )
            }
        )
    )
    results = await collect(name, make_event)
    assert "未能解析出有效的运势信息" in results[0]["data"]


async def test_xingzuo_unexpected_response(patch_httpx, make_event):
    name = "白羊座"
    patch_httpx(
        FakeHttpxClient(get={url_for(name): FakeHttpxResponse(json_data={"code": 0})})
    )
    results = await collect(name, make_event)
    assert "API响应未知" in results[0]["data"]


async def test_xingzuo_http_error(patch_httpx, make_event):
    name = "白羊座"
    patch_httpx(FakeHttpxClient(get={url_for(name): FakeHttpxResponse(status=503)}))
    results = await collect(name, make_event)
    assert "请求API时出错: 503" in results[0]["data"]


async def test_xingzuo_request_error(patch_httpx, make_event):
    name = "白羊座"
    url = url_for(name)
    patch_httpx(
        FakeHttpxClient(
            get={url: httpx.RequestError("offline", request=httpx.Request("GET", url))}
        )
    )
    results = await collect(name, make_event)
    assert "连接API失败" in results[0]["data"]
