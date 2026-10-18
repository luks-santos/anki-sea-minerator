import json
import tomllib
from pathlib import Path

ROOT = Path(__file__).parent.parent
MANIFEST = ROOT / "src" / "seaminerator" / "manifest.json"


def manifest():
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


def project_version():
    with (ROOT / "pyproject.toml").open("rb") as file:
        return tomllib.load(file)["project"]["version"]


def test_manifest_shows_the_project_version():
    assert manifest()["human_version"] == project_version()


def test_manifest_requires_anki_25_07():
    # The vendored anyio needs Python 3.10+, and Anki ships Python 3.13 from
    # 25.07 on: older releases (Python 3.9) can't even import the add-on.
    assert manifest()["min_point_version"] == 250700


def test_manifest_max_version_only_records_the_last_tested_release():
    # A positive max doesn't stop newer Anki releases from loading the
    # add-on; only a negative one would.
    assert manifest()["max_point_version"] > 0


def test_manifest_points_to_the_repository():
    assert manifest()["homepage"] == "https://github.com/luks-santos/anki-sea-minerator"
