"""handlers.sad_word_handler 单元测试。"""

import httpx
from treasure_bag.handlers.sad_word_handler import SAD_WORD_API_URL, get_sad_word

from tests.fakes import FakeHttpxClient, FakeHttpxResponse


async def collect(event):
    return [item async for item in get_sad_word(event)]


def client_with(**kwargs):
    return FakeHttpxClient(get={SAD_WORD_API_URL: FakeHttpxResponse(**kwargs)})


async def test_get_sad_word_success(make_event, patch_httpx):
    patch_httpx(client_with(json_data=[{"qinggan": "今天也要开心呀"}]))
    results = await collect(make_event("/sad-word"))
    assert results == [{"type": "plain", "data": "今天也要开心呀"}]


async def test_get_sad_word_bad_payload(make_event, patch_httpx):
    patch_httpx(client_with(json_data={"not": "a list"}))
    results = await collect(make_event("/sad-word"))
    assert "获取伤感语录失败" in results[0]["data"]


async def test_get_sad_word_empty_list(make_event, patch_httpx):
    patch_httpx(client_with(json_data=[]))
    results = await collect(make_event("/sad-word"))
    assert "获取伤感语录失败" in results[0]["data"]


async def test_get_sad_word_http_status_error(make_event, patch_httpx):
    patch_httpx(client_with(status=500))
    results = await collect(make_event("/sad-word"))
    assert "请求API时出错: 500" in results[0]["data"]


async def test_get_sad_word_request_error(make_event, patch_httpx):
    patch_httpx(
        FakeHttpxClient(
            get={
                SAD_WORD_API_URL: httpx.RequestError(
                    "offline", request=httpx.Request("GET", SAD_WORD_API_URL)
                )
            }
        )
    )
    results = await collect(make_event("/sad-word"))
    assert "连接API失败" in results[0]["data"]
