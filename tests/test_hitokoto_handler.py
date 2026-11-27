"""handlers.hitokoto_handler 单元测试。"""

import aiohttp
from treasure_bag.handlers.hitokoto_handler import get_hitokoto

from tests.fakes import FakeAiohttpSession, FakeResponse

URL = "https://v1.hitokoto.cn/"


async def test_get_hitokoto_with_author(make_event, patch_aiohttp):
    session = patch_aiohttp(
        FakeAiohttpSession(
            get={
                URL: FakeResponse(
                    json_data={
                        "hitokoto": "风很温柔",
                        "from_who": "小乔",
                        "from": "王者",
                    }
                )
            }
        )
    )
    result = await get_hitokoto(make_event("/hitokoto"))
    assert result["type"] == "plain"
    assert result["data"] == "\n风很温柔 —— 小乔 《王者》"
    assert session.calls[0][1] == URL


async def test_get_hitokoto_without_author(make_event, patch_aiohttp):
    patch_aiohttp(
        FakeAiohttpSession(
            get={
                URL: FakeResponse(json_data={"hitokoto": "一言", "from": " somewhere"})
            }
        )
    )
    result = await get_hitokoto(make_event("/hitokoto"))
    assert result["data"] == "\n一言 —— 《 somewhere》"


async def test_get_hitokoto_http_error(make_event, patch_aiohttp):
    patch_aiohttp(FakeAiohttpSession(get={URL: FakeResponse(status=500)}))
    result = await get_hitokoto(make_event("/hitokoto"))
    assert result["data"] == "抱歉，获取一言失败了。"


async def test_get_hitokoto_network_error(make_event, patch_aiohttp):
    patch_aiohttp(FakeAiohttpSession(get={URL: aiohttp.ClientError("boom")}))
    result = await get_hitokoto(make_event("/hitokoto"))
    assert "意料之外的错误" in result["data"]
