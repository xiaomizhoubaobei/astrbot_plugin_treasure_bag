"""baidu.beauty_handler 单元测试。"""

import base64
import json as _json
from unittest.mock import AsyncMock, patch

import pytest
from astrbot.api import message_components
from treasure_bag.baidu import beauty_handler
from treasure_bag.baidu.beauty_handler import (
    call_baidu_face_api,
    generate_face_analysis_report,
    get_beauty_score,
    get_image_as_base64,
)

from tests.fakes import FakeAiohttpSession, FakeResponse

IMAGE_URL = "https://example.com/face.jpg"
DETECT_URL_PREFIX = "https://aip.baidubce.com/rest/2.0/face/v3/detect?access_token="


async def collect(event):
    return [await get_beauty_score(event)]


def event_with_image(make_event):
    return make_event("", segments=[message_components.Image(IMAGE_URL)])


def face_info(**overrides):
    data = {
        "beauty": 88,
        "age": 18,
        "gender": {"type": "female"},
        "emotion": {"type": "smile"},
        "glasses": {"type": "none"},
        "face_shape": {"type": "oval"},
        "face_probability": 0.99,
        "angle": {"yaw": 1.0, "pitch": -2.0, "roll": 3.0},
        "quality": {
            "blur": 0.1,
            "illumination": 150,
            "completeness": 1,
            "score": 90,
        },
        "liveness": {"livemapscore": 0.9},
        "spoofing": 0.01,
        "mask": {"type": 0},
        "eye_status": {"left_eye": 0.9, "right_eye": 0.8},
    }
    data.update(overrides)
    return data


# ---- generate_face_analysis_report ----


def test_report_contains_core_fields():
    report = generate_face_analysis_report(face_info())
    assert "这位美女的颜值评分为：88分" in report
    assert "倾国倾城" in report
    assert "年龄大约：18岁" in report
    assert "当前表情：微笑" in report
    assert "脸型判断：椭圆脸" in report
    assert "真人" in report
    assert "真实照片" in report


def test_report_male_and_beauty_tiers():
    low = generate_face_analysis_report(
        face_info(beauty=30, gender={"type": "male"}, age=40)
    )
    assert "这位帅哥" in low
    assert "可能需要美颜相机" in low


def test_report_unknown_gender_and_default_face_shape():
    report = generate_face_analysis_report(
        face_info(gender={"type": "other"}, face_shape={"type": "diamond"})
    )
    assert "这位人物" in report
    assert "脸型判断：未知脸型" in report


def test_report_quality_warnings():
    report = generate_face_analysis_report(
        face_info(
            quality={
                "blur": 0.9,
                "illumination": 20,
                "completeness": 0,
                "occlusion": {"left_eye": 0.8, "nose": 0.5},
            }
        )
    )
    assert "照片有点模糊" in report
    assert "照片光线有点暗" in report
    assert "人脸可能不完整" in report
    assert "左眼" in report and "鼻子" in report


def test_report_eye_and_mask_details():
    report = generate_face_analysis_report(
        face_info(
            eye_status={"left_eye": 0.1, "right_eye": -1},
            mask={"type": 1},
            liveness={"livemapscore": 0.6},
            spoofing=0.9,
        )
    )
    assert "左眼 闭眼" in report
    assert "右眼 未知" in report
    assert "戴口罩" in report
    assert "可能是真人" in report
    assert "可能是合成图片" in report


# ---- call_baidu_face_api ----


def face_api_session(response):
    url = DETECT_URL_PREFIX + "test-token"
    return FakeAiohttpSession(post={url: response})


async def test_call_face_api_success(patch_aiohttp):
    face = face_info()
    session = patch_aiohttp(
        face_api_session(
            FakeResponse(
                status=200,
                text_data=_json.dumps(
                    {"error_code": 0, "result": {"face_num": 1, "face_list": [face]}}
                ),
            )
        )
    )
    assert await call_baidu_face_api("test-token", "base64data") == face
    method, url, kwargs = session.calls[0]
    assert method == "POST"
    assert url == DETECT_URL_PREFIX + "test-token"
    assert kwargs["json"]["image"] == "base64data"
    assert kwargs["json"]["image_type"] == "BASE64"


async def test_call_face_api_no_face(patch_aiohttp):
    patch_aiohttp(
        face_api_session(
            FakeResponse(
                status=200,
                text_data=_json.dumps({"error_code": 0, "result": {"face_num": 0}}),
            )
        )
    )
    assert "未检测到清晰人像" in await call_baidu_face_api("test-token", "b64")


async def test_call_face_api_error_code_222202(patch_aiohttp):
    patch_aiohttp(
        face_api_session(
            FakeResponse(status=200, text_data=_json.dumps({"error_code": 222202}))
        )
    )
    assert "未检测到清晰人像" in await call_baidu_face_api("test-token", "b64")


async def test_call_face_api_qps_limit(patch_aiohttp):
    patch_aiohttp(
        face_api_session(
            FakeResponse(status=200, text_data=_json.dumps({"error_code": 18}))
        )
    )
    assert "请求太快" in await call_baidu_face_api("test-token", "b64")


async def test_call_face_api_generic_error(patch_aiohttp):
    patch_aiohttp(
        face_api_session(
            FakeResponse(
                status=200,
                text_data=_json.dumps({"error_code": 1, "error_msg": "参数错误"}),
            )
        )
    )
    assert "参数错误" in await call_baidu_face_api("test-token", "b64")


async def test_call_face_api_invalid_json(patch_aiohttp):
    patch_aiohttp(face_api_session(FakeResponse(status=200, text_data="not json")))
    assert "返回异常" in await call_baidu_face_api("test-token", "b64")


async def test_call_face_api_http_error(patch_aiohttp):
    patch_aiohttp(face_api_session(FakeResponse(status=500)))
    assert "暂时不可用" in await call_baidu_face_api("test-token", "b64")


# ---- get_image_as_base64 ----


async def test_get_image_as_base64(patch_aiohttp):
    patch_aiohttp(
        FakeAiohttpSession(get={IMAGE_URL: FakeResponse(content=b"\x89PNG\r\n\x1a\n")})
    )
    assert (
        await get_image_as_base64(IMAGE_URL)
        == base64.b64encode(b"\x89PNG\r\n\x1a\n").decode()
    )


async def test_get_image_as_base64_unwraps_qq_url(patch_aiohttp, monkeypatch):
    from urllib.parse import quote

    inner = "https://qq.example.com/pic.jpg?x=1"
    qq_url = f"https://multimedia.nt.qq.com.cn?url={quote(inner, safe='')}"
    session = patch_aiohttp(
        FakeAiohttpSession(get={inner: FakeResponse(content=b"img")})
    )
    assert await get_image_as_base64(qq_url) == base64.b64encode(b"img").decode()
    assert session.calls[0][1] == inner


async def test_get_image_as_base64_http_error(patch_aiohttp):
    patch_aiohttp(FakeAiohttpSession(get={IMAGE_URL: FakeResponse(status=404)}))
    with pytest.raises(Exception, match="状态码: 404"):
        await get_image_as_base64(IMAGE_URL)


# ---- get_beauty_score (集成各步骤) ----


async def test_beauty_score_no_image(make_event, patch_aiohttp):
    with patch.object(
        beauty_handler, "get_baidu_access_token", new=AsyncMock(return_value="t")
    ):
        results = await collect(make_event(""))
    assert "请发送一张图片" in results[0]["data"]


async def test_beauty_score_token_failure(make_event, patch_aiohttp):
    with patch.object(
        beauty_handler, "get_baidu_access_token", new=AsyncMock(return_value=None)
    ):
        results = await collect(event_with_image(make_event))
    assert "获取百度API凭证失败" in results[0]["data"]


async def test_beauty_score_token_error(make_event, patch_aiohttp):
    with patch.object(
        beauty_handler,
        "get_baidu_access_token",
        new=AsyncMock(side_effect=RuntimeError("boom")),
    ):
        results = await collect(event_with_image(make_event))
    assert "获取百度API凭证时发生错误" in results[0]["data"]


async def test_beauty_score_success(make_event, patch_aiohttp):
    url = DETECT_URL_PREFIX + "tok"
    patch_aiohttp(
        FakeAiohttpSession(
            post={
                url: FakeResponse(
                    status=200,
                    text_data=_json.dumps(
                        {
                            "error_code": 0,
                            "result": {"face_num": 1, "face_list": [face_info()]},
                        }
                    ),
                )
            },
            get={IMAGE_URL: FakeResponse(content=b"img")},
        )
    )
    with patch.object(
        beauty_handler, "get_baidu_access_token", new=AsyncMock(return_value="tok")
    ):
        results = await collect(event_with_image(make_event))
    assert results[0]["type"] == "plain"
    assert "颜值评分为：88分" in results[0]["data"]


async def test_beauty_score_api_error_string(make_event, patch_aiohttp):
    with (
        patch.object(
            beauty_handler, "get_baidu_access_token", new=AsyncMock(return_value="tok")
        ),
        patch.object(
            beauty_handler, "get_image_as_base64", new=AsyncMock(return_value="b64")
        ),
        patch.object(
            beauty_handler,
            "call_baidu_face_api",
            new=AsyncMock(return_value="请求太快啦，请稍等片刻再试~"),
        ),
    ):
        results = await collect(event_with_image(make_event))
    assert results[0]["data"] == "请求太快啦，请稍等片刻再试~"
