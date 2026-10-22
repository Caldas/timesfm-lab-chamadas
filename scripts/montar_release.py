"""Build the release assets: a slim run-only bundle (zip and tar.gz), the sample CSV and checksums.

The bundle has what is needed to RUN the lab (installers, launchers, requirements, docs, notebooks,
sample data and the compiled package as a wheel), not the project's source tree, tests or CI.

Usage:
    python scripts/montar_release.py                  # writes to dist/release
    python scripts/montar_release.py --saida pasta
"""

from __future__ import annotations

import argparse
import calendar
import hashlib
import io
import re
import subprocess
import sys
import tarfile
import tempfile
import time
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# What goes into the bundle, relative to the repository root. Directories are copied whole.
INCLUDE_DIRS = ["docs", "notebooks", "requirements", "data/samples"]
INCLUDE_FILES = ["LICENSE", "CHANGELOG.md", "data/README.md"]
# Scripts for users. Maintainer tools (this script, regenerating the sample) stay out.
INCLUDE_SCRIPTS = [
    "abrir_interface.bat",
    "abrir_interface.command",
    "abrir_interface.sh",
    "baixar_datasets.py",
    "instalar_mac.command",
    "instalar_windows.bat",
    "setup_linux.sh",
    "setup_mac.sh",
    "setup_windows.ps1",
    "verificar_ambiente.py",
]
FORBIDDEN_TOP_LEVEL = {"src", "tests", ".github", "app", "pyproject.toml", ".gitattributes", ".gitignore"}
EXECUTABLE = (".sh", ".command")
CRLF_FILES = (".bat", ".ps1")
LF_TEXT = (".py", ".md", ".txt", ".csv", ".ipynb", ".toml", ".sh", ".command", ".yml", ".json")


def version() -> str:
    text = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    match = re.search(r'^version\s*=\s*"([^"]+)"', text, re.MULTILINE)
    if not match:
        raise SystemExit("Não achei a versão no pyproject.toml.")
    return match.group(1)


def normalize(name: str, data: bytes) -> bytes:
    """Line endings the way users need them: CRLF for Windows scripts, LF for everything else."""
    if name.endswith(CRLF_FILES):
        return data.replace(b"\r\n", b"\n").replace(b"\n", b"\r\n")
    if name.endswith(LF_TEXT):
        return data.replace(b"\r\n", b"\n")
    return data


def file_mode(name: str) -> int:
    return 0o755 if name.endswith(EXECUTABLE) else 0o644


def bundle_files() -> dict[str, Path]:
    """Bundle path (relative, with forward slashes) -> source file, without the wheel."""
    files: dict[str, Path] = {}
    for directory in INCLUDE_DIRS:
        for path in sorted((ROOT / directory).rglob("*")):
            if path.is_file() and "__pycache__" not in path.parts and not path.name.endswith(".pyc"):
                files[path.relative_to(ROOT).as_posix()] = path
    for name in INCLUDE_FILES:
        files[name] = ROOT / name
    for script in INCLUDE_SCRIPTS:
        files[f"scripts/{script}"] = ROOT / "scripts" / script
    files["LEIA-ME.md"] = ROOT / "release" / "LEIA-ME.md"
    missing = [name for name, path in files.items() if not path.exists()]
    if missing:
        raise SystemExit(f"Arquivos do pacote não encontrados: {missing}")
    leaked = {name.split("/")[0] for name in files} & FORBIDDEN_TOP_LEVEL
    if leaked:
        raise SystemExit(f"O pacote não pode conter: {sorted(leaked)}")
    return files


def build_wheel(dest: Path) -> Path:
    """Compile the package into a wheel (pure Python, so it works on every system)."""
    dest.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [sys.executable, "-m", "pip", "wheel", str(ROOT), "--no-deps", "--wheel-dir", str(dest)],
        check=True,
        cwd=ROOT,
    )
    wheels = sorted(dest.glob("callcenter_lab-*.whl"))
    if len(wheels) != 1:
        raise SystemExit(f"Esperava 1 wheel em {dest}, achei {len(wheels)}.")
    return wheels[0]


def commit_time() -> tuple[int, int, int, int, int, int]:
    """Fixed timestamp for the archive entries (the last commit), so rebuilds are reproducible."""
    try:
        out = subprocess.run(
            ["git", "log", "-1", "--format=%ct"], cwd=ROOT, capture_output=True, text=True, check=True
        ).stdout.strip()
        return time.gmtime(int(out))[:6]
    except (subprocess.SubprocessError, ValueError, OSError):
        return (2026, 1, 1, 0, 0, 0)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    digest.update(path.read_bytes())
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument("--saida", type=Path, default=ROOT / "dist" / "release")
    args = parser.parse_args()

    ver = version()
    out = args.saida
    out.mkdir(parents=True, exist_ok=True)
    root_name = f"timesfm-lab-chamadas-{ver}"

    with tempfile.TemporaryDirectory() as tmp:
        wheel = build_wheel(Path(tmp))
        entries: dict[str, bytes] = {}
        for name, path in bundle_files().items():
            entries[name] = normalize(name, path.read_bytes())
        entries[f"wheels/{wheel.name}"] = wheel.read_bytes()

    stamp = commit_time()
    zip_path = out / f"timesfm-lab-chamadas-v{ver}.zip"
    tar_path = out / f"timesfm-lab-chamadas-v{ver}.tar.gz"

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as archive:
        for name in sorted(entries):
            info = zipfile.ZipInfo(f"{root_name}/{name}", date_time=stamp)
            info.create_system = 3  # Unix, so that unzip applies the permissions below
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = (0o100000 | file_mode(name)) << 16
            archive.writestr(info, entries[name])

    with tarfile.open(tar_path, "w:gz") as archive:
        for name in sorted(entries):
            info = tarfile.TarInfo(f"{root_name}/{name}")
            info.size = len(entries[name])
            info.mode = file_mode(name)
            info.mtime = calendar.timegm(stamp)
            info.uid = info.gid = 0
            info.uname = info.gname = ""
            archive.addfile(info, io.BytesIO(entries[name]))

    sample = out / "chamadas_sinteticas.csv"
    sample.write_bytes(entries["data/samples/chamadas_sinteticas.csv"])

    assets = [zip_path, tar_path, sample]
    (out / "SHA256SUMS.txt").write_text(
        "".join(f"{sha256(p)} *{p.name}\n" for p in assets), encoding="utf-8", newline="\n"
    )
    print(f"Pacote enxuto ({len(entries)} arquivos, sem código-fonte do projeto):")
    for p in [*assets, out / "SHA256SUMS.txt"]:
        print(f"  {p.name}  {p.stat().st_size:,} bytes")
    return 0


if __name__ == "__main__":
    sys.exit(main())
