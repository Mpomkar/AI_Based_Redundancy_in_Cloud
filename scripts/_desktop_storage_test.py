"""Verify accepted uploads land under Desktop/Uploaded Files."""
from __future__ import annotations

import json
import random
import string
import subprocess
import sys
import tempfile
import urllib.request
from pathlib import Path

from PIL import Image

from app.config import settings

BASE = "http://127.0.0.1:8000"


def api(method, path, token=None, data=None):
    url = BASE + path
    body = json.dumps(data).encode() if data is not None else None
    headers = {"Content-Type": "application/json"} if data is not None else {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    with urllib.request.urlopen(req, timeout=45) as resp:
        raw = resp.read().decode()
        return json.loads(raw) if raw.strip() else {}


def upload(token: str, path: Path, filename: str) -> dict:
    out = subprocess.check_output(
        [
            "curl",
            "-s",
            "-X",
            "POST",
            f"{BASE}/api/upload",
            "-H",
            f"Authorization: Bearer {token}",
            "-F",
            f"file=@{path};filename={filename};type=image/png",
        ]
    ).decode()
    return json.loads(out)


def main() -> int:
    tag = "".join(random.choices(string.ascii_lowercase, k=6))
    admin = api("POST", "/api/auth/login", data={"username": "admin", "password": "ADMIN123"})
    at = admin["access_token"]
    u = f"store{tag}"
    created = api(
        "POST",
        "/api/admin/users",
        token=at,
        data={"username": u, "password": "TEST123", "role": "user"},
    )
    tok = api("POST", "/api/auth/login", data={"username": u, "password": "TEST123"})["access_token"]

    tmp = Path(tempfile.gettempdir()) / f"saved_{tag}.png"
    Image.new("RGB", (52, 52), (200, 10, 30)).save(tmp)
    up = upload(tok, tmp, f"saved_{tag}.png")
    print("decision:", up.get("decision"))
    print("storage_dir:", settings.storage_dir)

    user_dir = settings.storage_dir / settings.uploads_subdir / str(created["id"])
    files = list(user_dir.glob(f"saved_{tag}_*.png")) if user_dir.is_dir() else []
    print("user_dir:", user_dir)
    print("files:", files)

    if up.get("decision") != "stored":
        print("FAIL: expected stored")
        return 1
    if not files or files[0].stat().st_size <= 0:
        print("FAIL: file missing on Desktop")
        return 1

    # Unsupported must not be written
    bad = Path(tempfile.gettempdir()) / f"bad_{tag}.txt"
    bad.write_text("nope", encoding="utf-8")
    code = subprocess.check_output(
        [
            "curl",
            "-s",
            "-o",
            "NUL",
            "-w",
            "%{http_code}",
            "-X",
            "POST",
            f"{BASE}/api/upload",
            "-H",
            f"Authorization: Bearer {tok}",
            "-F",
            f"file=@{bad};filename=bad_{tag}.txt;type=text/plain",
        ]
    ).decode()
    print("txt_code:", code)
    if code != "400" or list(user_dir.glob(f"bad_{tag}*")):
        print("FAIL: rejected file leaked to disk")
        return 1

    api("DELETE", f"/api/admin/users/{created['id']}", token=at)
    print("DESKTOP_STORE_OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
