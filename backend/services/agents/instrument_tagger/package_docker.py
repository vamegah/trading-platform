#!/usr/bin/env python3
"""Package the InstrumentTagger Lambda using Docker."""
import argparse
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

HANDLER_FILES = ["lambda_handler.py", "agent.py", "templates.py", "observability.py"]

REQUIRED_PACKAGES = [
    "boto3",
    "pydantic",
    "python-dotenv",
    "tenacity",
    "openai-agents[litellm]",
    "langfuse",
]

LAMBDA_IMAGE = "public.ecr.aws/lambda/python:3.12"


def _run(cmd):
    print("Running:", " ".join(cmd))
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        print(r.stderr)
        sys.exit(1)
    return r.stdout


def package() -> Path:
    tagger_dir = Path(__file__).parent.resolve()
    backend_dir = tagger_dir.parents[2]
    db_dir = backend_dir / "db"

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        (tmp_path / "requirements.txt").write_text("\n".join(REQUIRED_PACKAGES))

        _run([
            "docker", "run", "--rm",
            "--platform", "linux/amd64",
            "-v", f"{tmp_path}:/build",
            "-v", f"{db_dir}:/db",
            "--entrypoint", "/bin/bash",
            LAMBDA_IMAGE,
            "-c",
            "cd /build && "
            "pip install --target ./package -r requirements.txt && "
            "pip install --target ./package --no-deps /db",
        ])

        package_dir = tmp_path / "package"
        for name in HANDLER_FILES:
            src = tagger_dir / name
            if src.exists():
                shutil.copy(src, package_dir)
            else:
                print(f"Warning: missing {name}")

        zip_path = tagger_dir / "tagger_lambda.zip"
        if zip_path.exists():
            zip_path.unlink()

        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for f in package_dir.rglob("*"):
                if f.is_file():
                    zf.write(f, f.relative_to(package_dir))

        size_mb = zip_path.stat().st_size / (1024 * 1024)
        print(f"Package created: {zip_path} ({size_mb:.1f} MB)")
        return zip_path


def deploy(zip_path: Path, function_name: str) -> None:
    import boto3
    client = boto3.client("lambda")
    with open(zip_path, "rb") as f:
        response = client.update_function_code(FunctionName=function_name, ZipFile=f.read())
    print("Deployed:", response["FunctionArn"])


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--deploy", action="store_true")
    parser.add_argument("--function-name", default="trading-tagger")
    args = parser.parse_args()

    _run(["docker", "--version"])
    zip_path = package()
    if args.deploy:
        deploy(zip_path, args.function_name)


if __name__ == "__main__":
    main()