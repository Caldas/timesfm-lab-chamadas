import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location("montar_release", ROOT / "scripts" / "montar_release.py")
montar = importlib.util.module_from_spec(spec)
spec.loader.exec_module(montar)


def test_bundle_has_what_is_needed_to_run_but_no_project_source():
    names = set(montar.bundle_files())
    tops = {name.split("/")[0] for name in names}
    assert not tops & montar.FORBIDDEN_TOP_LEVEL  # no src, tests, .github, app, pyproject
    for needed in ("LEIA-ME.md", "LICENSE", "scripts/setup_linux.sh", "scripts/instalar_windows.bat",
                   "scripts/instalar_mac.command", "scripts/baixar_datasets.py",
                   "requirements/windows.txt", "data/samples/chamadas_sinteticas.csv", "docs/01-instalar.md"):
        assert needed in names, needed
    assert "scripts/montar_release.py" not in names  # maintainer tool


def test_line_endings_and_modes():
    assert montar.normalize("a.bat", b"x\ny\r\nz") == b"x\r\ny\r\nz"
    assert montar.normalize("a.sh", b"x\r\ny") == b"x\ny"
    assert montar.normalize("a.bin", b"x\r\ny") == b"x\r\ny"
    assert montar.file_mode("scripts/setup_linux.sh") == 0o755
    assert montar.file_mode("scripts/instalar_mac.command") == 0o755
    assert montar.file_mode("docs/00-conceitos.md") == 0o644


def test_version_matches_the_package():
    from callcenter_lab import __version__

    assert montar.version() == __version__
