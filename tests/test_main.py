"""main.py 插件入口与命令注册单元测试。"""

from unittest.mock import AsyncMock, patch

import pytest
from astrbot.api import AstrBotConfig
from astrbot.api.event import filter
from treasure_bag.main import TreasureBagPlugin


@pytest.fixture
def plugin():
    with patch("treasure_bag.main.init_baidu_credentials") as init:
        instance = TreasureBagPlugin(None, AstrBotConfig())
        init.assert_called_once()
    return instance


def test_commands_registered():
    expected = {
        "hitokoto",
        "bdrate_beauty",
        "kog_info",
        "handwrite",
        "beauty_img",
        "sad-word",
        "今日运势",
        "weather",
        "treasurebag-help",
    }
    assert expected.issubset(filter.command_registry.keys())


def test_command_aliases():
    registry = filter.command_registry
    assert set(registry["beauty_img"]._command_aliases) == {
        "random_beauty",
        "daily_beauty",
        "random_beauty_image",
    }
    assert set(registry["sad-word"]._command_aliases) == {
        "伤感一言",
        "每日伤感",
        "伤感语录",
        "情感",
    }


async def test_help_command(plugin, make_event):
    results = [r async for r in plugin.help_command(make_event("/treasurebag-help"))]
    assert len(results) == 1
    text = results[0]["data"]
    assert "百宝袋插件帮助" in text
    for cmd in ("/hitokoto", "/kog_info", "/今日运势", "/treasurebag-help"):
        assert cmd in text


async def test_hitokoto_command_delegates(plugin, make_event):
    event = make_event("/hitokoto")
    with patch(
        "treasure_bag.main.get_hitokoto",
        new=AsyncMock(return_value={"type": "plain", "data": "一句话"}),
    ) as mock:
        assert [r async for r in plugin.hitokoto_command(event)] == [
            {"type": "plain", "data": "一句话"}
        ]
    mock.assert_awaited_once_with(event)


async def test_kog_info_command_streams_results(plugin, make_event):
    async def fake(event):
        yield {"type": "plain", "data": "1"}
        yield {"type": "plain", "data": "2"}

    with patch("treasure_bag.main.wangzhe_command", new=fake):
        results = [
            r async for r in plugin.kog_info_command(make_event("/kog_info 亚瑟"))
        ]
    assert [r["data"] for r in results] == ["1", "2"]


async def test_xingzuo_command_passes_name(plugin, make_event):
    event = make_event("/今日运势 白羊座")

    async def fake(event, name):
        yield {"type": "plain", "data": name}

    with patch("treasure_bag.main.xingzuo_command", new=fake):
        results = [
            r async for r in plugin.xingzuo_command(event, xingzuo_name="白羊座")
        ]
    assert results[0]["data"] == "白羊座"


async def test_weather_command_delegates(plugin, make_event):
    event = make_event("/weather 北京")

    async def fake(event):
        yield {"type": "plain", "data": "晴"}

    with patch("treasure_bag.main.weather_command", new=fake):
        results = [r async for r in plugin.weather_command(event)]
    assert results[0]["data"] == "晴"


async def test_handwrite_command_delegates(plugin, make_event):
    async def fake(event):
        yield {"type": "image", "data": "url"}

    with patch("treasure_bag.main.handwrite_command", new=fake):
        results = [
            r async for r in plugin.handwrite_command(make_event("/handwrite hi"))
        ]
    assert results[0]["type"] == "image"


async def test_beauty_img_command_delegates(plugin, make_event):
    async def fake(event):
        yield {"type": "image", "data": "url"}

    with patch("treasure_bag.main.beauty_img_command", new=fake):
        results = [
            r async for r in plugin.beauty_img_command(make_event("/beauty_img"))
        ]
    assert results[0]["type"] == "image"


async def test_sad_word_command_delegates(plugin, make_event):
    async def fake(event):
        yield {"type": "plain", "data": "伤感"}

    with patch("treasure_bag.main.get_sad_word", new=fake):
        results = [r async for r in plugin.sad_word_command(make_event("/sad-word"))]
    assert results[0]["data"] == "伤感"


async def test_bdrate_beauty_command_delegates(plugin, make_event):
    event = make_event("/bdrate_beauty")
    with patch(
        "treasure_bag.main.get_beauty_score",
        new=AsyncMock(return_value={"type": "plain", "data": "分"}),
    ) as mock:
        results = [r async for r in plugin.bdrate_beauty_command(event)]
    assert results[0]["data"] == "分"
    mock.assert_awaited_once_with(event)
