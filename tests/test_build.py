import os
import shutil
import subprocess
import zipfile
from pathlib import Path

import pytest

BUILD = Path(__file__).parent.parent / "scripts" / "build.sh"

pytestmark = pytest.mark.skipif(shutil.which("bash") is None, reason="needs bash")


def build(tmp_path) -> list[str]:
    # A stand-in add-on folder, laid out like src/seaminerator once Anki has
    # run it through the development junction.
    src = tmp_path / "addon"
    (src / "_vendor" / "httpx").mkdir(parents=True)
    (src / "_vendor" / "httpx" / "__init__.py").write_text("")
    (src / "__init__.py").write_text("")
    (src / "manifest.json").write_text('{"package": "x", "name": "X"}')
    (src / "config.json").write_text("{}")
    (src / "meta.json").write_text('{"config": {"api_key": "secret"}}')
    (src / "user_files").mkdir()
    (src / "user_files" / "notes.txt").write_text("mine")
    (src / "__pycache__").mkdir()
    (src / "__pycache__" / "x.cpython-313.pyc").write_bytes(b"")
    out = tmp_path / "dist" / "test.ankiaddon"

    env = {**os.environ, "SRC": src.as_posix(), "OUT": out.as_posix()}
    subprocess.run(["bash", BUILD.as_posix()], env=env, check=True, capture_output=True)
    with zipfile.ZipFile(out) as archive:
        return archive.namelist()


def test_the_package_never_carries_the_users_settings(tmp_path):
    # Anki saves the settings, API keys included, to meta.json in the add-on
    # folder: a package built from a used folder must leave it out.
    names = build(tmp_path)
    assert "meta.json" not in names
    assert not [name for name in names if name.startswith("user_files")]


def test_the_package_holds_the_add_on_at_its_root(tmp_path):
    names = build(tmp_path)
    assert {"__init__.py", "manifest.json", "config.json"} <= set(names)
    assert "_vendor/httpx/__init__.py" in names
    compiled = [n for n in names if "__pycache__" in n or n.endswith(".pyc")]
    assert not compiled
