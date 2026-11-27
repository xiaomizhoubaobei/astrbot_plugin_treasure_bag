"""Build a complete AstrBot upload archive without installing anything."""

import argparse
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PACKAGE_DIRS = ("handlers", "baidu", "config", "utils")


def build(output: Path | None = None) -> Path:
    """Validate inputs and build a distributable ZIP archive."""
    metadata = (ROOT / "metadata.yaml").read_text(encoding="utf-8")
    lines = metadata.splitlines()
    name = ""
    for line in lines:
        if line.startswith("name:"):
            name = line.split(":", 1)[1].strip()
            break
    if not name or any(c in name for c in " \t\r\n/\\;$`|&()"):
        raise ValueError("metadata.yaml 中的 name 非法")

    required = [
        ROOT / entry
        for entry in (
            "__init__.py",
            "main.py",
            "metadata.yaml",
            "requirements.txt",
            "LICENSE",
            "README.md",
            "CHANGELOG.md",
            "logo.png",
            "build_release.py",
        )
    ]
    for package_dir in PACKAGE_DIRS:
        required.append(ROOT / package_dir / "__init__.py")
        required += sorted((ROOT / package_dir).glob("*.py"))
    for path in required:
        if not path.is_file():
            raise FileNotFoundError(f"打包缺少必需文件: {path.relative_to(ROOT)}")

    output = Path(output) if output is not None else ROOT / f"{name}.zip"
    output.parent.mkdir(parents=True, exist_ok=True)
    files = set(required)
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(files):
            archive.write(path, (Path(name) / path.relative_to(ROOT)).as_posix())
    with zipfile.ZipFile(output) as archive:
        if archive.testzip() is not None:
            raise RuntimeError("ZIP 完整性校验失败")
    return output


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    print(build(args.output))
