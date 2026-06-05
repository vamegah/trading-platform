import json
import sys
import urllib.request
from urllib.parse import urlparse


def _validated_http_url(url: str) -> str:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise SystemExit(f"unsupported smoke-test URL: {url}")
    return url


def get_json(url: str) -> dict:
    with urllib.request.urlopen(_validated_http_url(url), timeout=10) as response:  # nosec B310
        return json.loads(response.read().decode("utf-8"))


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("usage: python scripts/smoke_test.py <base_url>")
    base_url = sys.argv[1].rstrip("/")
    health = get_json(f"{base_url}/health")
    ready = get_json(f"{base_url}/ready")
    if health.get("status") != "healthy":
        raise SystemExit(f"health check failed: {health}")
    if ready.get("ready") is not True:
        raise SystemExit(f"readiness check failed: {ready}")
    print(json.dumps({"status": "passed", "base_url": base_url}, sort_keys=True))


if __name__ == "__main__":
    main()
