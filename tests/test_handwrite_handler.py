"""handlers.handwrite_handler 单元测试。"""

from urllib.parse import quote, unquote

from treasure_bag.handlers.handwrite_handler import handwrite_command


async def collect(event):
    return [item async for item in handwrite_command(event)]


async def test_handwrite_empty_input(make_event):
    results = await collect(make_event("/handwrite"))
    assert results[0]["type"] == "plain"
    assert "请输入要转换成手写体" in results[0]["data"]


async def test_handwrite_generates_image_url(make_event):
    results = await collect(make_event("/handwrite 你好世界"))
    assert len(results) == 1
    assert results[0]["type"] == "image"
    assert results[0]["data"].startswith("https://zj.v.api.aa1.cn/api/zuoye/?msg=")
    encoded = results[0]["data"].split("msg=", 1)[1]
    assert unquote(encoded) == "你好世界"


async def test_handwrite_url_encodes_special_chars(make_event):
    results = await collect(make_event("/handwrite a b&c"))
    encoded = results[0]["data"].split("msg=", 1)[1]
    assert encoded == quote("a b&c")
