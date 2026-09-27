"""Quick smoke test for presentation-critical API flows."""
from __future__ import annotations

import json
import random
import string
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request
from pathlib import Path

from PIL import Image, ImageDraw

BASE = "http://127.0.0.1:8000"


def req(
    method: str,
    path: str,
    token: str | None = None,
    data: dict | None = None,
    files: dict | None = None,
):
    url = BASE + path
    if files:
        cmd = ["curl", "-s", "-X", method, url]
        if token:
            cmd += ["-H", f"Authorization: Bearer {token}"]
        for key, fpath in files.items():
            cmd += ["-F", f"{key}=@{fpath};type=image/png"]
        out = subprocess.check_output(cmd).decode("utf-8", errors="replace")
        return json.loads(out) if out.strip() else {}

    headers: dict[str, str] = {}
    body = None
    if data is not None:
        body = json.dumps(data).encode()
        headers["Content-Type"] = "application/json"
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=30) as resp:
            raw = resp.read().decode()
            if not raw.strip():
                return {"_status": resp.status}
            return json.loads(raw)
    except urllib.error.HTTPError as e:
        raw = e.read().decode()
        try:
            detail = json.loads(raw)
        except Exception:
            detail = raw
        raise RuntimeError(f"{method} {path} -> {e.code}: {detail}") from e


def main() -> int:
    ok = 0
    fail = 0

    def check(name: str, cond: bool, detail: str = ""):
        nonlocal ok, fail
        if cond:
            ok += 1
            print(f"PASS  {name}")
        else:
            fail += 1
            print(f"FAIL  {name} {detail}")

    health = req("GET", "/api/health")
    check("health", health.get("status") == "ok")

    admin = req("POST", "/api/auth/login", data={"username": "ADMIN", "password": "ADMIN123"})
    check("admin login case-insensitive", admin.get("user", {}).get("role") == "admin")
    at = admin["access_token"]

    user = req("POST", "/api/auth/login", data={"username": "user", "password": "USER123"})
    check("user login", user.get("user", {}).get("role") == "user")
    ut = user["access_token"]

    try:
        req("POST", "/api/auth/login", data={"username": "admin", "password": "wrong"})
        check("bad login rejected", False)
    except RuntimeError as e:
        check("bad login rejected", "401" in str(e))

    try:
        req("GET", "/api/stats", token=ut)
        check("user blocked from admin stats", False)
    except RuntimeError as e:
        check("user blocked from admin stats", "403" in str(e))

    tag = "".join(random.choices(string.ascii_lowercase, k=6))
    u1 = f"a{tag}"
    u2 = f"b{tag}"
    c1 = req(
        "POST",
        "/api/admin/users",
        token=at,
        data={"username": u1, "password": "TEST123", "role": "user"},
    )
    c2 = req(
        "POST",
        "/api/admin/users",
        token=at,
        data={"username": u2, "password": "TEST123", "role": "user"},
    )
    check("create user1", c1.get("username") == u1)
    check("create user2", c2.get("username") == u2)

    tmp = Path(tempfile.gettempdir())
    fa = tmp / f"uniq_a_{tag}.png"
    fb = tmp / f"uniq_b_{tag}.png"
    img = Image.new(
        "RGB",
        (160, 100),
        (random.randint(0, 255), random.randint(0, 255), random.randint(0, 255)),
    )
    d = ImageDraw.Draw(img)
    d.rectangle([5, 5, 155, 95], outline=(255, 255, 255), width=4)
    d.line([5, 5, 155, 95], fill=(0, 0, 0), width=2)
    d.text((40, 40), tag, fill=(255, 255, 0))
    img.save(fa)
    img.save(fb)

    # Fresh users have empty libraries — avoids false pHash hits from admin history
    t1 = req("POST", "/api/auth/login", data={"username": u1, "password": "TEST123"})["access_token"]
    t2 = req("POST", "/api/auth/login", data={"username": u2, "password": "TEST123"})["access_token"]

    up1 = req("POST", "/api/upload", token=t1, files={"file": str(fa)})
    check("user1 unique upload stored", up1.get("decision") == "stored", str(up1.get("decision")))
    check("user1 upload toast", bool(up1.get("toast_message")))

    up2 = req("POST", "/api/upload", token=t2, files={"file": str(fb)})
    check(
        "cross-user same content -> stored_shared 0KB",
        up2.get("decision") == "stored_shared" and up2.get("size_bytes") == 0,
        f"decision={up2.get('decision')} size={up2.get('size_bytes')}",
    )
    check("cross-user toast mentions shared", "0 KB" in (up2.get("toast_message") or ""))

    up3 = req("POST", "/api/upload", token=t2, files={"file": str(fb)})
    check("same-user exact dup rejected", up3.get("decision") == "rejected_duplicate")

    events = req("GET", "/api/events?limit=5", token=at)
    check("admin events include username", isinstance(events, list) and "username" in events[0])

    req("PATCH", f"/api/admin/users/{c1['id']}", token=at, data={"is_active": False})
    try:
        req("POST", "/api/auth/login", data={"username": u1, "password": "TEST123"})
        check("inactive user cannot login", False)
    except RuntimeError as e:
        check("inactive user cannot login", "401" in str(e))

    req("PATCH", f"/api/admin/users/{c1['id']}", token=at, data={"is_active": True})
    deleted = req("DELETE", f"/api/admin/users/{c1['id']}", token=at)
    check("delete user1", "_status" in deleted or deleted == {})
    req("DELETE", f"/api/admin/users/{c2['id']}", token=at)
    check("delete user2", True)

    try:
        req("DELETE", f"/api/admin/users/{admin['user']['id']}", token=at)
        check("cannot delete self", False)
    except RuntimeError as e:
        check("cannot delete self", "400" in str(e))

    root = req("GET", "/")
    check("root friendly message", "5173" in root.get("message", ""))

    print()
    print(f"Result: {ok} passed, {fail} failed")
    return 1 if fail else 0


if __name__ == "__main__":
    sys.exit(main())
