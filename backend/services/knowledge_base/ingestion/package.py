#!/usr/bin/env python3
"""
Build Lambda deployment packages using uv, from any host OS.

Usage:
    python package_lambda.py                     # build all lambdas in ./lambdas/
    python package_lambda.py --lambda ingest     # build only one
    python package_lambda.py --all --out dist/
    python package_lambda.py --zip-ingest        # add zip fallback (no uv)
    python package_lambda.py --dry-run           # show what would be built

Design goals:
- Correct for the Lambda *runtime*, not the host.
- One zip per Lambda, with a manifest describing provenance.
- Fail loudly if a file is missing or a wheel is incompatible.
- Optional Lambda Layer output for large deps.
- Deterministic, reproducible-ish artifacts (pinned deps required).
- Cross-platform: Windows, macOS (Intel/ARM), Linux.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import shutil
import subprocess
import sys
import tempfile
import time
import zipfile
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Optional


# ---------------------------------------------------------------------------
# CONFIG
# ---------------------------------------------------------------------------

ROOT = Path(__file__).resolve().parent
DEFAULT_LAMBDAS_DIR = ROOT / "lambdas"
DEFAULT_OUT_DIR = ROOT / "dist"
DEFAULT_BUILD_DIR = ROOT / ".build"

# Lambda runtime target. Override with env or --target.
DEFAULT_PYTHON_VERSION = os.getenv("LAMBDA_PYTHON_VERSION", "3.12")
DEFAULT_PLATFORM = os.getenv(
    "LAMBDA_PLATFORM", "x86_64-manylinux2014"
)  # or aarch64-manylinux2014

# Files/dirs excluded from the deployment zip
EXCLUDE_NAMES = {
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    "tests",
    "test",
    "docs",
    "doc",
    "examples",
    ".git",
    ".github",
}
EXCLUDE_SUFFIXES = {".pyc", ".pyo", ".pyd", ".c", ".h", ".pyx"}
EXCLUDE_PATTERNS = {"*.dist-info/RECORD"}  # optional trimming; see config


# ---------------------------------------------------------------------------
# DATA TYPES
# ---------------------------------------------------------------------------

@dataclass
class LambdaSpec:
    name: str
    handler: str
    source_files: list[str] = field(default_factory=list)
    requirements: Optional[str] = None  # path to a requirements file
    runtime: str = f"python{DEFAULT_PYTHON_VERSION}"
    timeout: int = 60
    memory: int = 1024


@dataclass
class BuildResult:
    name: str
    zip_path: Path
    size_mb: float
    manifest_path: Path
    duration_s: float
    layer_zip: Optional[Path] = None


# ---------------------------------------------------------------------------
# HELPERS
# ---------------------------------------------------------------------------

def log(msg: str) -> None:
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)


def die(msg: str, code: int = 1) -> None:
    print(f"ERROR: {msg}", file=sys.stderr, flush=True)
    sys.exit(code)


def sha256_file(path: Path, chunk: int = 1 << 20) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(chunk), b""):
            h.update(block)
    return h.hexdigest()


def human_size(num_bytes: int) -> str:
    mb = num_bytes / (1024 * 1024)
    return f"{mb:.2f} MB"


# ---------------------------------------------------------------------------
# LAMBDA DISCOVERY
# ---------------------------------------------------------------------------

def discover_lambdas(lambdas_dir: Path) -> list[LambdaSpec]:
    """
    Discover Lambda specs by convention:
        lambdas/<name>/
            handler.py
            requirements.txt
            manifest.json    (optional; overrides defaults)
    """
    if not lambdas_dir.exists():
        die(f"Lambdas dir not found: {lambdas_dir}")

    specs: list[LambdaSpec] = []
    for entry in sorted(lambdas_dir.iterdir()):
        if not entry.is_dir() or entry.name.startswith((".", "_")):
            continue

        manifest_file = entry / "manifest.json"
        req_file = entry / "requirements.txt"
        py_files = sorted(p.name for p in entry.glob("*.py"))

        if not py_files:
            log(f"skip {entry.name}: no .py files")
            continue

        if manifest_file.exists():
            data = json.loads(manifest_file.read_text())
            specs.append(
                LambdaSpec(
                    name=data.get("name", entry.name),
                    handler=data.get("handler", f"{py_files[0][:-3]}.lambda_handler"),
                    source_files=data.get("source_files", py_files),
                    requirements=str(req_file) if req_file.exists() else None,
                    runtime=data.get("runtime", f"python{DEFAULT_PYTHON_VERSION}"),
                    timeout=int(data.get("timeout", 60)),
                    memory=int(data.get("memory", 1024)),
                )
            )
        else:
            specs.append(
                LambdaSpec(
                    name=entry.name,
                    handler=f"{py_files[0][:-3]}.lambda_handler",
                    source_files=py_files,
                    requirements=str(req_file) if req_file.exists() else None,
                )
            )
    return specs


# ---------------------------------------------------------------------------
# DEPENDENCY RESOLUTION (uv)
# ---------------------------------------------------------------------------

def _uv_available() -> bool:
    return shutil.which("uv") is not None


def install_dependencies_uv(
    requirements: Path,
    target_dir: Path,
    python_version: str,
    platform_tag: str,
) -> None:
    """
    Install dependencies into target_dir using `uv pip install --target`.

    Cross-platform: uv resolves wheels for the *target* platform regardless
    of host, so this works from Windows/macOS/Linux and produces
    Lambda-compatible artifacts.
    """
    if not _uv_available():
        die(
            "`uv` not found on PATH. Install it (https://docs.astral.sh/uv/) "
            "or pass --zip-fallback to use pip --target instead."
        )

    target_dir.mkdir(parents=True, exist_ok=True)

    cmd = [
        "uv",
        "pip",
        "install",
        "--target",
        str(target_dir),
        "--python-version",
        python_version,
        "--python-platform",
        platform_tag,
        "--no-cache",
        "--only-binary",
        ":all:",  # refuse to compile from source → guarantees Linux wheels
        "-r",
        str(requirements),
    ]
    log(f"uv pip install → target={target_dir} python={python_version} platform={platform_tag}")
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        print(proc.stdout)
        print(proc.stderr, file=sys.stderr)
        die("uv pip install failed")


def install_dependencies_pip_fallback(
    requirements: Path,
    target_dir: Path,
    python_version: str,
    platform_tag: str,
) -> None:
    """
    Fallback when uv is unavailable. Uses pip with --platform/--only-binary,
    which requires `pip>=23.1` and does NOT work on some older pips.
    """
    target_dir.mkdir(parents=True, exist_ok=True)

    # pip expects tags like manylinux2014_x86_64 (underscore, not dash)
    pip_platform = platform_tag.replace("-", "_")
    py_tag = f"cp{python_version.replace('.', '')}"

    cmd = [
        sys.executable,
        "-m",
        "pip",
        "install",
        "--target",
        str(target_dir),
        "--platform",
        pip_platform,
        "--python-version",
        python_version,
        "--implementation",
        "cp",
        "--only-binary",
        ":all:",
        "--upgrade",
        "-r",
        str(requirements),
    ]
    log(f"pip install --target={target_dir} platform={pip_platform} python={py_tag}")
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        print(proc.stdout)
        print(proc.stderr, file=sys.stderr)
        die(
            "pip install failed. Ensure pip>=23.1 is installed, or use uv "
            "(recommended)."
        )


# ---------------------------------------------------------------------------
# FILE FILTERING
# ---------------------------------------------------------------------------

def _should_include(path: Path, strip: bool) -> bool:
    name = path.name
    if name in EXCLUDE_NAMES:
        return False
    if path.suffix in EXCLUDE_SUFFIXES:
        return False
    if strip:
        # Optional trim: tests, docs, RECORD files, and typing stubs
        if any(part in {"tests", "test", "docs", "doc", "examples"} for part in path.parts):
            return False
        if name == "RECORD" and path.parent.suffix == ".dist-info":
            return False
        if path.suffix in {".md", ".rst", ".txt"} and path.name.lower() in {
            "readme.md", "readme.rst", "license", "license.txt",
        }:
            return False
    return True


def copy_tree(src: Path, dst: Path, strip: bool = True) -> int:
    """Copy src → dst, applying exclusion rules. Returns file count."""
    count = 0
    for root, dirs, files in os.walk(src):
        root_path = Path(root)
        rel = root_path.relative_to(src)
        target_root = dst / rel
        target_root.mkdir(parents=True, exist_ok=True)

        dirs[:] = [d for d in dirs if d not in EXCLUDE_NAMES]
        for f in files:
            fp = root_path / f
            if not _should_include(fp, strip):
                continue
            shutil.copy2(fp, target_root / f)
            count += 1
    return count


# ---------------------------------------------------------------------------
# ZIP CREATION
# ---------------------------------------------------------------------------

def create_zip(source_dir: Path, zip_path: Path) -> None:
    """
    Zip source_dir → zip_path with forward-slash arcnames (cross-platform).
    Deterministic-ish: sorted walk, fixed timestamp for reproducible builds
    when SOURCE_DATE_EPOCH is set.
    """
    source_date = int(os.getenv("SOURCE_DATE_EPOCH", "0")) or None

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        for root, dirs, files in os.walk(source_dir):
            dirs[:] = [d for d in dirs if d not in EXCLUDE_NAMES]
            dirs.sort()
            for f in sorted(files):
                fp = Path(root) / f
                if not _should_include(fp, strip=True):
                    continue
                arcname = fp.relative_to(source_dir).as_posix()
                if source_date:
                    info = zipfile.ZipInfo(arcname, date_time=time.gmtime(source_date)[:6])
                    info.compress_type = zipfile.ZIP_DEFLATED
                    info.external_attr = 0o644 << 16
                    with fp.open("rb") as fh:
                        zf.writestr(info, fh.read())
                else:
                    zf.write(fp, arcname)


# ---------------------------------------------------------------------------
# LAYER SUPPORT
# ---------------------------------------------------------------------------

LAYER_SIZE_SOFT_LIMIT_MB = 50  # unzipped
LAYER_SIZE_HARD_LIMIT_MB = 250


def maybe_build_layer(
    deps_dir: Path,
    name: str,
    out_dir: Path,
) -> Optional[Path]:
    """
    If deps exceed the direct-upload soft limit, produce a layer zip.
    Layers must place deps under python/ at the zip root.
    """
    total = sum(f.stat().st_size for f in deps_dir.rglob("*") if f.is_file())
    size_mb = total / (1024 * 1024)
    if size_mb < LAYER_SIZE_SOFT_LIMIT_MB:
        return None

    if size_mb > LAYER_SIZE_HARD_LIMIT_MB:
        die(
            f"Dependencies for '{name}' are {size_mb:.1f} MB, exceeding the "
            f"250 MB layer limit. Split into multiple layers or trim deps."
        )

    layer_stage = deps_dir.parent / f"{name}-layer"
    layer_python = layer_stage / "python"
    if layer_python.exists():
        shutil.rmtree(layer_python)
    layer_python.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(deps_dir, layer_python)

    layer_zip = out_dir / f"{name}-layer.zip"
    create_zip(layer_stage, layer_zip)
    shutil.rmtree(layer_stage, ignore_errors=True)
    log(f"  → layer built: {layer_zip.name} ({human_size(layer_zip.stat().st_size)})")
    return layer_zip


# ---------------------------------------------------------------------------
# BUILD PIPELINE
# ---------------------------------------------------------------------------

def build_one(
    spec: LambdaSpec,
    lambdas_dir: Path,
    out_dir: Path,
    build_root: Path,
    python_version: str,
    platform_tag: str,
    use_uv: bool,
    strip: bool,
    version: str,
) -> BuildResult:
    started = time.monotonic()
    src_dir = lambdas_dir / spec.name
    if not src_dir.exists():
        die(f"Lambda source dir not found: {src_dir}")

    # ---- Validate source files exist ----
    missing = [f for f in spec.source_files if not (src_dir / f).exists()]
    if missing:
        die(f"Missing source files for {spec.name}: {missing}")

    # ---- Stage ----
    stage_dir = build_root / spec.name / "package"
    if stage_dir.parent.exists():
        shutil.rmtree(stage_dir.parent)
    stage_dir.mkdir(parents=True, exist_ok=True)

    # ---- Dependencies ----
    if spec.requirements:
        req_path = Path(spec.requirements)
        if not req_path.exists():
            die(f"requirements.txt not found: {req_path}")
        deps_target = build_root / spec.name / "deps"
        deps_target.mkdir(parents=True, exist_ok=True)

        if use_uv:
            install_dependencies_uv(req_path, deps_target, python_version, platform_tag)
        else:
            install_dependencies_pip_fallback(req_path, deps_target, python_version, platform_tag)

        # Merge deps into the package
        shutil.copytree(deps_target, stage_dir, dirs_exist_ok=True)

    # ---- Source files ----
    for f in spec.source_files:
        shutil.copy2(src_dir / f, stage_dir / f)
    # Copy non-.py assets if any (templates, json configs)
    for extra in src_dir.glob("*.json"):
        shutil.copy2(extra, stage_dir / extra.name)

    # ---- Optional trim pass ----
    if strip:
        _trim_stage(stage_dir)

    # ---- Layer decision ----
    layer_zip = maybe_build_layer(
        build_root / spec.name / "deps" if spec.requirements else Path("/dev/null"),
        spec.name,
        out_dir,
    ) if spec.requirements else None

    # ---- Zip ----
    versioned_name = f"{spec.name}-{version}.zip"
    zip_path = out_dir / versioned_name
    out_dir.mkdir(parents=True, exist_ok=True)
    create_zip(stage_dir, zip_path)

    size_bytes = zip_path.stat().st_size
    size_mb = size_bytes / (1024 * 1024)

    # ---- Manifest ----
    manifest = {
        "name": spec.name,
        "handler": spec.handler,
        "runtime": spec.runtime,
        "timeout": spec.timeout,
        "memory": spec.memory,
        "version": version,
        "built_at_utc": datetime.now(timezone.utc).isoformat(),
        "built_on": {
            "host_os": platform.system(),
            "host_arch": platform.machine(),
            "host_python": platform.python_version(),
        },
        "target": {
            "python_version": python_version,
            "platform": platform_tag,
        },
        "artifact": {
            "filename": versioned_name,
            "size_bytes": size_bytes,
            "sha256": sha256_file(zip_path),
        },
        "layer": layer_zip.name if layer_zip else None,
        "source_files": spec.source_files,
        "requirements": spec.requirements,
        "installer": "uv" if use_uv else "pip",
    }
    manifest_path = out_dir / f"{spec.name}-{version}.manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2))

    duration = time.monotonic() - started

    return BuildResult(
        name=spec.name,
        zip_path=zip_path,
        size_mb=size_mb,
        manifest_path=manifest_path,
        duration_s=duration,
        layer_zip=layer_zip,
    )


def _trim_stage(stage: Path) -> None:
    """Remove caches, test dirs, and non-essential files from a staged package."""
    for root, dirs, _ in os.walk(stage):
        dirs[:] = [d for d in dirs if d not in EXCLUDE_NAMES]
        for d in list(dirs):
            if d in EXCLUDE_NAMES:
                shutil.rmtree(Path(root) / d, ignore_errors=True)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Build Lambda deployment packages using uv.",
    )
    p.add_argument(
        "--lambdas-dir",
        default=str(DEFAULT_LAMBDAS_DIR),
        help="Directory containing one subdir per Lambda.",
    )
    p.add_argument(
        "--out",
        default=str(DEFAULT_OUT_DIR),
        help="Output directory for zips + manifests.",
    )
    p.add_argument(
        "--lambda",
        dest="only",
        action="append",
        default=[],
        help="Build only this lambda (repeatable).",
    )
    p.add_argument(
        "--python-version",
        default=DEFAULT_PYTHON_VERSION,
        help="Target Python version (default 3.12).",
    )
    p.add_argument(
        "--platform",
        default=DEFAULT_PLATFORM,
        help="Target platform tag (x86_64-manylinux2014 or aarch64-manylinux2014).",
    )
    p.add_argument(
        "--pip-fallback",
        action="store_true",
        help="Use pip instead of uv (less reliable cross-platform).",
    )
    p.add_argument(
        "--no-strip",
        action="store_true",
        help="Do not strip tests/docs/readmes from dependencies.",
    )
    p.add_argument(
        "--version",
        default=os.getenv("BUILD_VERSION", datetime.now().strftime("%Y%m%d%H%M")),
        help="Version string embedded in filenames + manifest.",
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="List what would be built; do nothing.",
    )
    return p


def main(argv: Optional[list[str]] = None) -> int:
    args = _build_parser().parse_args(argv)

    lambdas_dir = Path(args.lambdas_dir).resolve()
    out_dir = Path(args.out).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    specs = discover_lambdas(lambdas_dir)
    if args.only:
        wanted = set(args.only)
        specs = [s for s in specs if s.name in wanted]
        missing = wanted - {s.name for s in specs}
        if missing:
            die(f"Requested lambdas not found: {sorted(missing)}")

    if not specs:
        die("No lambdas discovered.")

    log(
        f"Building {len(specs)} lambda(s) | target={args.python_version}/"
        f"{args.platform} | installer={'pip' if args.pip_fallback else 'uv'} | "
        f"out={out_dir}"
    )
    for s in specs:
        log(f"  • {s.name}  handler={s.handler}  srcs={s.source_files}")

    if args.dry_run:
        log("dry-run: exiting")
        return 0

    build_root = Path(tempfile.mkdtemp(prefix="lambda-build-"))
    results: list[BuildResult] = []
    try:
        for spec in specs:
            log(f"── building {spec.name} ──")
            results.append(
                build_one(
                    spec=spec,
                    lambdas_dir=lambdas_dir,
                    out_dir=out_dir,
                    build_root=build_root,
                    python_version=args.python_version,
                    platform_tag=args.platform,
                    use_uv=not args.pip_fallback,
                    strip=not args.no_strip,
                    version=args.version,
                )
            )
    finally:
        shutil.rmtree(build_root, ignore_errors=True)

    print()
    log("Build summary")
    for r in results:
        flags = []
        if r.size_mb > 50:
            flags.append(">50MB")
        if r.layer_zip:
            flags.append("LAYER")
        flag_str = f" [{', '.join(flags)}]" if flags else ""
        log(
            f"  ✓ {r.name}: {r.zip_path.name} "
            f"({r.size_mb:.2f} MB) in {r.duration_s:.1f}s{flag_str}"
        )
        log(f"      manifest: {r.manifest_path.name}")

    total_mb = sum(r.size_mb for r in results)
    log(f"Total: {total_mb:.2f} MB across {len(results)} artifact(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())