"""先注册测试桩，再启动 coverage 运行 pytest，输出覆盖率摘要与 coverage.xml。

直接用 ``coverage run -m pytest`` 时，coverage 会在 conftest 建立包视图前解析
``--source``，导致覆盖率数据为空。本脚本把顺序固定为「建桩 -> 建包视图 -> 开 coverage」。

用法::

    python -m tests.run_coverage                  # 全量测试 + 覆盖率
    python -m tests.run_coverage -- -k models     # "--" 之后透传给 pytest
"""

from __future__ import annotations

import sys
from pathlib import Path

from coverage import Coverage

# 关键顺序：先由 conftest 建立 AstrBot 桩与 treasure_bag 包视图，再构造 Coverage
import tests.conftest  # noqa: F401

PACKAGE_NAME = "treasure_bag"
REPO_ROOT = Path(__file__).resolve().parents[1]
_XML_PATH = REPO_ROOT / "coverage.xml"
_OMIT = ["tests/*", "*/tests/*"]
_PYTEST_ARGS = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else ["tests"]


def main() -> int:
    """运行测试、打印覆盖率报告并写 coverage.xml，返回 pytest 退出码。"""
    cov = Coverage(source=[PACKAGE_NAME], omit=_OMIT, config_file=False)
    cov.start()
    try:
        import pytest

        code = pytest.main(["-q", *_PYTEST_ARGS])
    finally:
        cov.stop()
        cov.save()

    # 测试失败也出报告，便于分辨「用例失败」还是「覆盖率口径不对」
    cov.report()
    cov.xml_report(outfile=str(_XML_PATH))
    print(f"[coverage] XML 已写出：{_XML_PATH}")
    return int(code)


if __name__ == "__main__":
    raise SystemExit(main())
