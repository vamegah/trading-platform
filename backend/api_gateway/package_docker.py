#!/usr/bin/env python3
"""Package the API Gateway Lambda using Docker."""
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path


def _run(cmd, cwd=None):
    print("Running:", " ".join(cmd))
    r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    if r.returncode != 0:
        print(r.stderr)
        sys.exit(1)
    return r.stdout


def main() -> None:
    api_dir = Path(__file__).parent.resolve()
    backend_dir = api_dir.parents[1]
    db_dir = backend_dir / "db"

    try:
        _run(["docker", "info"])
    except Exception:
        print("Docker is not available")
        sys.exit(1)

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        package_dir = tmp_path / "package"
        package_dir.mkdir()

        # Copy the API package as `api/`
        shutil.copytree(
            api_dir, package_dir / "api",
            ignore=shutil.ignore_patterns(
                "__pycache__", "*.pyc", ".env*", "*.zip",
                "package_docker.py", "test_*.py",
            ),
        )
        shutil.copy2(api_dir / "lambda_handler.py", package_dir / "lambda_handler.py")

        # Copy the platform DB module
        if (db_dir / "client.py").exists():
            shutil.copytree(
                db_dir, package_dir / "db",
                ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "migrations", "tests"),
            )

        requirements = package_dir / "requirements.txt"
        requirements.write_text("\n".join([
            "fastapi>=0.116.0",
            "uvicorn>=0.35.0",
            "mangum>=0.19.0",
            "boto3>=1.40.0",
            "fastapi-clerk-auth>=0.0.7",
            "pydantic>=2.11.0",
            "python-dotenv>=1.1.0",
            "tenacity>=9.1.0",
        ]))

        (package_dir / "Dockerfile").write_text("""
FROM public.ecr.aws/lambda/python:3.12
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt -t /var/task
COPY . /var/task/
CMD ["api.main.handler"]
""")

        print("Building Docker image...")
        _run([
            "docker", "build", "--platform", "linux/amd64",
            "-t", "trading-api-packager", ".",
        ], cwd=package_dir)

        container = "trading-api-extract"
        _run(["docker", "rm", "-f", container], cwd=package_dir)
        _run(["docker", "create", "--name", container, "trading-api-packager"], cwd=package_dir)

        extract_dir = tmp_path / "lambda"
        extract_dir.mkdir()
        _run(["docker", "cp", f"{container}:/var/task/.", str(extract_dir)])
        _run(["docker", "rm", "-f", container])

        zip_path = api_dir / "api_lambda.zip"
        if zip_path.exists():
            zip_path.unlink()

        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for f in extract_dir.rglob("*"):
                if f.is_file() and not f.name.endswith(".pyc") and "__pycache__" not in f.parts:
                    zf.write(f, f.relative_to(extract_dir))

        size_mb = zip_path.stat().st_size / (1024 * 1024)
        print(f"Package created: {zip_path} ({size_mb:.2f} MB)")


if __name__ == "__main__":
    main()