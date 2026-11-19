#!/usr/bin/env python3
"""
Package the scheduler Lambda into lambda_function.zip for Terraform deployment.

The scheduler only uses stdlib (urllib, json, logging, os) — no pip deps needed.
The zip just contains lambda_function.py.

Usage:
    uv run package.py
"""

import os
import sys
import zipfile
from pathlib import Path


def create_deployment_package() -> str:
    current_dir = Path(__file__).parent
    zip_path = current_dir / "lambda_function.zip"
    handler = current_dir / "lambda_function.py"

    if not handler.exists():
        print(f"Error: {handler} not found.")
        sys.exit(1)

    if zip_path.exists():
        os.remove(zip_path)

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.write(handler, "lambda_function.py")

    size_kb = zip_path.stat().st_size / 1024
    print(f"✅ Deployment package created: {zip_path}  ({size_kb:.1f} KB)")
    return str(zip_path)


if __name__ == "__main__":
    create_deployment_package()
