#!/usr/bin/env python3
"""
Package the Portfolio Planner Lambda using Docker.

Produces a zip that is byte-compatible with the AWS Lambda Python 3.12 runtime.
"""
import argparse
import os
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

HANDLER_FILES = [
    "lambda_handler.py",
    "agent.py",
    "templates.py",
    "market.py",
    "prices.py",
    "observability.py",
]

REQUIRED_PACKAGES = [
    # shared with the DB layer
    "boto3",
    "pydantic",
    "python-dotenv",
    "tenacity",
    # planner-specific
    "openai-agents[litellm]",
    "polygon-api-client",
    "langfuse",
]

LAMBDA_IMAGE = "public.ecr.aws/lambda/python:3.12"


def _run(cmd: list[str], cwd: Path | None = None) -> str:
    print("Running:", " ".join(cmd))
    result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    if result.returncode != 0:
        print(result.stderr)
        sys.exit(1)
    return result.stdout


def package() -> Path:
    planner_dir = Path(__file__).parent.resolve()
    backend_dir = planner_dir.parents[2]  # backend/
    # The platform DB package lives in backend/database/src. The handlers
    # import it as `db`, so it is copied into the zip under that name.
    db_src = backend_dir / "database" / "src"
    if not (db_src / "__init__.py").exists():
        print(f"Missing DB package: {db_src}")
        sys.exit(1)
    # The container writes as root. Hand the files back to this user so the
    # handler copy below works on Linux CI runners.
    owner = f"{os.getuid()}:{os.getgid()}" if hasattr(os, "getuid") else ""
    chown = f" && chown -R {owner} ./package" if owner else ""

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        requirements_file = tmp_path / "requirements.txt"
        requirements_file.write_text("\n".join(REQUIRED_PACKAGES))

        docker_cmd = [
            "docker", "run", "--rm",
            "--platform", "linux/amd64",
            "-v", f"{tmp_path}:/build",
            "-v", f"{db_src}:/db:ro",
            "--entrypoint", "/bin/bash",
            LAMBDA_IMAGE,
            "-c",
            "cd /build && "
            "(pip install --target ./package -r requirements.txt && "
            "cp -r /db ./package/db && "
            "rm -rf ./package/db/__pycache__); "
            "status=$?" + chown + "; exit $status",
        ]
        _run(docker_cmd)

        package_dir = tmp_path / "package"
        for name in HANDLER_FILES:
            src = planner_dir / name
            if src.exists():
                shutil.copy(src, package_dir)
            else:
                print(f"Warning: missing {name}")

        zip_path = planner_dir / "planner_lambda.zip"
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
    print(f"Deploying to {function_name}")
    with open(zip_path, "rb") as f:
        response = client.update_function_code(FunctionName=function_name, ZipFile=f.read())
    print(f"Deployed: {response['FunctionArn']}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--deploy", action="store_true")
    parser.add_argument("--function-name", default="trading-planner")
    args = parser.parse_args()

    _run(["docker", "--version"])
    zip_path = package()

    if args.deploy:
        deploy(zip_path, args.function_name)


if __name__ == "__main__":
    main()