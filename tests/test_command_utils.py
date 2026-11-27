"""utils.command_utils 单元测试。"""

from treasure_bag.utils.command_utils import extract_command_arg


def test_extract_arg_with_slash(make_event):
    event = make_event("/handwrite 你好世界")
    assert extract_command_arg(event, "handwrite") == "你好世界"


def test_extract_arg_without_slash(make_event):
    event = make_event("handwrite hello world")
    assert extract_command_arg(event, "handwrite") == "hello world"


def test_extract_arg_trims_extra_spaces(make_event):
    event = make_event("/handwrite   小乔真可爱   ")
    assert extract_command_arg(event, "handwrite") == "小乔真可爱"


def test_extract_arg_case_insensitive(make_event):
    event = make_event("/HANDWRITE ABC")
    assert extract_command_arg(event, "handwrite") == "ABC"


def test_extract_arg_returns_empty_when_no_arg(make_event):
    assert extract_command_arg(make_event("/handwrite"), "handwrite") == ""
    assert extract_command_arg(make_event("/handwrite   "), "handwrite") == ""


def test_extract_arg_returns_empty_for_unrelated_command(make_event):
    assert extract_command_arg(make_event("/weather 北京"), "handwrite") == ""


def test_extract_arg_ignores_non_text_segments(make_event):
    segments = [
        object(),  # 非文本段（如图片）应被忽略
        type("Text", (), {"text": "/handwrite"})(),
        type("Text", (), {"text": " 内容"})(),
    ]
    event = make_event("", segments=segments)
    assert extract_command_arg(event, "handwrite") == "内容"
