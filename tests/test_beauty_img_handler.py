"""handlers.beauty_img_handler 单元测试。"""

import aiohttp
from treasure_bag.handlers.beauty_img_handler import (
    BEAUTY_IMAGE_API_URL,
    _get_beauty_image_url,
    beauty_img_command,
)

from tests.fakes import FakeAiohttpSession, FakeResponse


async def collect(event):
    return [item async for item in beauty_img_command(event)]


async def test_get_url_adds_https_protocol(patch_aiohttp):
    patch_aiohttp(
        FakeAiohttpSession(
            get={BEAUTY_IMAGE_API_URL: FakeResponse(text_data="example.com/a.jpg")}
        )
    )
    assert await _get_beauty_image_url() == "https://example.com/a.jpg"


async def test_get_url_normalizes_protocol_relative(patch_aiohttp):
    patch_aiohttp(
        FakeAiohttpSession(
            get={
                BEAUTY_IMAGE_API_URL: FakeResponse(text_data="//cdn.example.com/a.jpg")
            }
        )
    )
    assert await _get_beauty_image_url() == "https://cdn.example.com/a.jpg"


async def test_get_url_keeps_existing_https(patch_aiohttp):
    patch_aiohttp(
        FakeAiohttpSession(
            get={BEAUTY_IMAGE_API_URL: FakeResponse(text_data="https://x/y.png")}
        )
    )
    assert await _get_beauty_image_url() == "https://x/y.png"


async def test_get_url_returns_none_on_http_error(patch_aiohttp):
    patch_aiohttp(
        FakeAiohttpSession(get={BEAUTY_IMAGE_API_URL: FakeResponse(status=503)})
    )
    assert await _get_beauty_image_url() is None


async def test_get_url_returns_none_on_network_error(patch_aiohttp):
    patch_aiohttp(
        FakeAiohttpSession(get={BEAUTY_IMAGE_API_URL: aiohttp.ClientError("boom")})
    )
    assert await _get_beauty_image_url() is None


async def test_beauty_img_command_success(make_event, patch_aiohttp):
    patch_aiohttp(
        FakeAiohttpSession(
            get={
                BEAUTY_IMAGE_API_URL: FakeResponse(text_data="//example.com/beauty.jpg")
            }
        )
    )
    results = await collect(make_event("/beauty_img"))
    assert results == [{"type": "image", "data": "https://example.com/beauty.jpg"}]


async def test_beauty_img_command_failure(make_event, patch_aiohttp):
    patch_aiohttp(
        FakeAiohttpSession(get={BEAUTY_IMAGE_API_URL: FakeResponse(status=500)})
    )
    results = await collect(make_event("/beauty_img"))
    assert results[0]["type"] == "plain"
    assert "获取图片失败" in results[0]["data"]
