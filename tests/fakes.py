"""轻量级异步 HTTP 测试替身，避免单测依赖真实网络。"""

from __future__ import annotations

import httpx


class FakeAsyncCM:
    """把普通对象包装成 async context manager。"""

    def __init__(self, value):
        self.value = value

    async def __aenter__(self):
        return self.value

    async def __aexit__(self, exc_type, exc, tb):
        return False


class FakeResponse:
    """aiohttp/httpx 响应对象的测试替身。"""

    def __init__(
        self,
        *,
        status: int = 200,
        json_data=None,
        text_data: str = "",
        content: bytes = b"",
        json_error: Exception | None = None,
    ):
        self.status = status
        self.status_code = status  # httpx 风格
        self._json_data = json_data
        self._text_data = text_data
        self._content = content
        self._json_error = json_error

    async def json(self):
        if self._json_error:
            raise self._json_error
        return self._json_data

    async def text(self):
        return self._text_data

    async def read(self):
        return self._content

    def raise_for_status(self):
        if self.status >= 400:
            request = httpx.Request("GET", "https://example.test")
            raise httpx.HTTPStatusError(
                f"HTTP {self.status}", request=request, response=self
            )


class FakeAiohttpSession:
    """按 URL 映射响应的 aiohttp.ClientSession 替身。"""

    def __init__(self, *, get=None, post=None):
        self.get_responses = get or {}
        self.post_responses = post or {}
        self.calls: list[tuple[str, str, dict]] = []

    def get(self, url: str, **kwargs):
        return self._request("GET", self.get_responses, url, kwargs)

    def post(self, url: str, **kwargs):
        return self._request("POST", self.post_responses, url, kwargs)

    def _request(self, method, responses, url, kwargs):
        self.calls.append((method, url, kwargs))
        result = responses.get(url)
        if isinstance(result, Exception):
            raise result
        return FakeAsyncCM(result if result is not None else FakeResponse(status=404))


class FakeHttpxResponse(FakeResponse):
    """httpx 响应替身：.json() 为同步方法。"""

    def json(self):
        if self._json_error:
            raise self._json_error
        return self._json_data


class FakeHttpxClient:
    """按 URL 映射响应的 httpx.AsyncClient 替身。"""

    def __init__(self, *, get=None):
        self.get_responses = get or {}
        self.calls: list[tuple[str, dict]] = []

    async def get(self, url: str, **kwargs):
        self.calls.append((url, kwargs))
        result = self.get_responses.get(url)
        if isinstance(result, Exception):
            raise result
        return result if result is not None else FakeResponse(status=404)


# 让假会话可以直接作为 async context manager 使用
async def _session_aenter(self):
    return self


async def _session_aexit(self, exc_type, exc, tb):
    return False


FakeAiohttpSession.__aenter__ = _session_aenter
FakeAiohttpSession.__aexit__ = _session_aexit
FakeHttpxClient.__aenter__ = _session_aenter
FakeHttpxClient.__aexit__ = _session_aexit
