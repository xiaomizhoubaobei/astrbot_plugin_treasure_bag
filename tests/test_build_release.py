"""build_release.build 单元测试。"""

import zipfile

import pytest
from treasure_bag.build_release import build


def test_build_creates_valid_archive(tmp_path):
    output = build(tmp_path / "plugin.zip")
    assert output.is_file()
    with zipfile.ZipFile(output) as archive:
        names = archive.namelist()
        assert "treasure_bag_plugin/main.py" in names
        assert "treasure_bag_plugin/handlers/hitokoto_handler.py" in names
        assert "treasure_bag_plugin/metadata.yaml" in names
        assert archive.testzip() is None


def test_build_rejects_illegal_metadata_name(monkeypatch, tmp_path):
    bad = tmp_path / "metadata.yaml"
    bad.write_text("name: bad/name\n", encoding="utf-8")
    monkeypatch.setattr("treasure_bag.build_release.ROOT", tmp_path)
    with pytest.raises(ValueError, match="非法"):
        build(tmp_path / "out.zip")


def test_build_rejects_missing_required_file(monkeypatch, tmp_path):
    (tmp_path / "metadata.yaml").write_text("name: some_plugin\n", encoding="utf-8")
    monkeypatch.setattr("treasure_bag.build_release.ROOT", tmp_path)
    with pytest.raises(FileNotFoundError, match="__init__.py"):
        build(tmp_path / "out.zip")
