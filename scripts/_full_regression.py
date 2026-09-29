"""Thorough pre-share regression suite."""
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
ok = fail = 0


def check(name: str, cond: bool, detail: str = "") -> None:
    global ok, fail
    if cond:
        ok += 1
        print(f"PASS  {name}")
    else:
        fail += 1
        print(f"FAIL  {name} {detail}")


def req(method, path, token=None, data=None, files=None):
    url = BASE + path
    if files:
        cmd = ["curl", "-s", "-w", "\n%{http_code}", "-X", method, url]
        if token:
            cmd += ["-H", f"Authorization: Bearer {token}"]
        for key, fpath in files.items():
            cmd += ["-F", f"{key}=@{fpath};type=image/png"]
        out = subprocess.check_output(cmd).decode("utf-8", errors="replace")
        body, _, code = out.rpartition("\n")
        code = code.strip()
        if code not in ("200", "201", "204"):
            raise RuntimeError(f"{method} {path} -> {code}: {body}")
        return json.loads(body) if body.strip() else {"_status": int(code)}
    headers = {}
    body = json.dumps(data).encode() if data is not None else None
    if data is not None:
        headers["Content-Type"] = "application/json"
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=45) as resp:
            raw = resp.read().decode()
            return json.loads(raw) if raw.strip() else {"_status": resp.status}
    except urllib.error.HTTPError as e:
        raw = e.read().decode()
        raise RuntimeError(f"{method} {path} -> {e.code}: {raw}") from e


def make_png(path: Path, label: str) -> None:
    """Highly unique noise images so same-user pHash does not false-reject."""
    rng = random.Random(f"{label}-{path.name}-{random.randbytes(8).hex()}")
    w, h = 220, 160
    pixels = [
        (rng.randint(0, 255), rng.randint(0, 255), rng.randint(0, 255))
        for _ in range(w * h)
    ]
    img = Image.new("RGB", (w, h))
    img.putdata(pixels)
    d = ImageDraw.Draw(img)
    for _ in range(12):
        x1, y1 = rng.randint(0, w - 1), rng.randint(0, h - 1)
        x2, y2 = rng.randint(0, w - 1), rng.randint(0, h - 1)
        d.line([x1, y1, x2, y2], fill=(rng.randint(0, 255),) * 3, width=3)
    d.ellipse(
        [rng.randint(0, 80), rng.randint(0, 60), rng.randint(100, 210), rng.randint(80, 150)],
        outline=(255, 255, 0),
        width=4,
    )
    d.text((10, 10), label[:18], fill=(255, 0, 0))
    img.save(path)


def main() -> int:
    tag = "".join(random.choices(string.ascii_lowercase, k=6))
    tmp = Path(tempfile.gettempdir())

    # 1) Health / root
    h = req("GET", "/api/health")
    check("health", h.get("status") == "ok")
    root = req("GET", "/")
    check("root message", "5173" in root.get("message", ""))

    # 2) Auth
    admin = req("POST", "/api/auth/login", data={"username": "ADMIN", "password": "ADMIN123"})
    check("admin login", admin["user"]["role"] == "admin")
    at = admin["access_token"]

    seeded = req("POST", "/api/auth/login", data={"username": "user", "password": "USER123"})
    check("seeded user login", seeded["user"]["role"] == "user")

    try:
        req("POST", "/api/auth/login", data={"username": "admin", "password": "wrong"})
        check("bad password rejected", False)
    except RuntimeError as e:
        check("bad password rejected", "401" in str(e))

    # 3) Create two users
    u1, u2 = f"s1{tag}", f"s2{tag}"
    c1 = req("POST", "/api/admin/users", token=at, data={"username": u1, "password": "TEST123", "role": "user"})
    c2 = req("POST", "/api/admin/users", token=at, data={"username": u2, "password": "TEST123", "role": "user"})
    check("create user1", c1["username"] == u1)
    check("create user2", c2["username"] == u2)
    t1 = req("POST", "/api/auth/login", data={"username": u1, "password": "TEST123"})["access_token"]
    t2 = req("POST", "/api/auth/login", data={"username": u2, "password": "TEST123"})["access_token"]

    # 4) User blocked from admin APIs
    for path in ("/api/stats", "/api/events", "/api/files", "/api/admin/users"):
        try:
            req("GET", path, token=t1)
            check(f"user blocked {path}", False)
        except RuntimeError as e:
            check(f"user blocked {path}", "403" in str(e))

    # 5) Uploads + visibility
    f1 = tmp / f"share_{tag}_u1.png"
    f2 = tmp / f"share_{tag}_u2.png"
    f_shared = tmp / f"share_{tag}_same_a.png"
    f_shared_b = tmp / f"share_{tag}_same_b.png"
    make_png(f1, f"u1-{tag}")
    make_png(f2, f"u2-{tag}")
    make_png(f_shared, f"same-{tag}")
    f_shared_b.write_bytes(f_shared.read_bytes())  # identical bytes, different name

    up1 = req("POST", "/api/upload", token=t1, files={"file": str(f1)})
    up2 = req("POST", "/api/upload", token=t2, files={"file": str(f2)})
    check("user1 store", up1.get("decision") == "stored", str(up1.get("decision")))
    check("user2 store", up2.get("decision") == "stored", str(up2.get("decision")))
    check("upload toast present", bool(up1.get("toast_message")))

    me1 = req("GET", "/api/me/events?limit=50", token=t1)
    me2 = req("GET", "/api/me/events?limit=50", token=t2)
    n1 = {e["original_name"] for e in me1}
    n2 = {e["original_name"] for e in me2}
    check("user1 own only", f1.name in n1 and f2.name not in n1)
    check("user2 own only", f2.name in n2 and f1.name not in n2)
    check("user1 user_id scoped", all(e["user_id"] == c1["id"] for e in me1))

    # 6) Cross-user 0KB shared
    up_a = req("POST", "/api/upload", token=t1, files={"file": str(f_shared)})
    check("first of pair stored", up_a.get("decision") == "stored", str(up_a.get("decision")))
    up_b = req("POST", "/api/upload", token=t2, files={"file": str(f_shared_b)})
    check(
        "cross-user 0KB shared",
        up_b.get("decision") == "stored_shared" and up_b.get("size_bytes") == 0,
        f"{up_b.get('decision')} size={up_b.get('size_bytes')}",
    )
    check("shared toast", "0 KB" in (up_b.get("toast_message") or ""))

    # 7) Same-user exact duplicate blocked
    dup = req("POST", "/api/upload", token=t2, files={"file": str(f_shared_b)})
    check("same-user duplicate blocked", dup.get("decision") == "rejected_duplicate")

    # 8) Admin sees all + filter
    all_ev = req("GET", "/api/events?limit=200", token=at)
    names = {e["original_name"] for e in all_ev}
    check("admin sees u1+u2 files", f1.name in names and f2.name in names)
    filt = req("GET", f"/api/events?user_id={c1['id']}&limit=50", token=at)
    check("admin filter user1", all(e["user_id"] == c1["id"] for e in filt) and f1.name in {e["original_name"] for e in filt})
    check("admin filter hides u2", f2.name not in {e["original_name"] for e in filt})
    check("admin events have username", any(e.get("username") for e in all_ev))

    stats = req("GET", "/api/stats", token=at)
    check("admin global stats", stats["total_upload_attempts"] >= 4)

    me_admin = req("GET", "/api/me/events?limit=100", token=at)
    check("admin /me own-only", all(e["user_id"] == admin["user"]["id"] for e in me_admin))

    # 9) Deactivate / delete / self-delete guard
    req("PATCH", f"/api/admin/users/{c1['id']}", token=at, data={"is_active": False})
    try:
        req("POST", "/api/auth/login", data={"username": u1, "password": "TEST123"})
        check("inactive cannot login", False)
    except RuntimeError as e:
        check("inactive cannot login", "401" in str(e))

    req("PATCH", f"/api/admin/users/{c1['id']}", token=at, data={"is_active": True})
    req("DELETE", f"/api/admin/users/{c1['id']}", token=at)
    req("DELETE", f"/api/admin/users/{c2['id']}", token=at)
    check("delete users", True)

    try:
        req("DELETE", f"/api/admin/users/{admin['user']['id']}", token=at)
        check("cannot delete self", False)
    except RuntimeError as e:
        check("cannot delete self", "400" in str(e))

    # 10) Users list for admin
    users = req("GET", "/api/admin/users", token=at)
    check("admin list users", isinstance(users, list) and any(u["username"] == "admin" for u in users))

    print()
    print(f"TOTAL: {ok} passed, {fail} failed")
    return 1 if fail else 0


if __name__ == "__main__":
    sys.exit(main())
