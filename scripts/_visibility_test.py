"""Verify admin sees all data; regular users see only their own."""
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
        if code.strip() not in ("200", "201", "204"):
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
        with urllib.request.urlopen(request, timeout=30) as resp:
            raw = resp.read().decode()
            return json.loads(raw) if raw.strip() else {"_status": resp.status}
    except urllib.error.HTTPError as e:
        raw = e.read().decode()
        raise RuntimeError(f"{method} {path} -> {e.code}: {raw}") from e


def main() -> int:
    ok = fail = 0

    def check(name, cond, detail=""):
        nonlocal ok, fail
        if cond:
            ok += 1
            print(f"PASS  {name}")
        else:
            fail += 1
            print(f"FAIL  {name} {detail}")

    tag = "".join(random.choices(string.ascii_lowercase, k=6))
    admin = req("POST", "/api/auth/login", data={"username": "admin", "password": "ADMIN123"})
    at = admin["access_token"]
    admin_id = admin["user"]["id"]

    u1name, u2name = f"v1{tag}", f"v2{tag}"
    c1 = req("POST", "/api/admin/users", token=at, data={"username": u1name, "password": "TEST123", "role": "user"})
    c2 = req("POST", "/api/admin/users", token=at, data={"username": u2name, "password": "TEST123", "role": "user"})
    t1 = req("POST", "/api/auth/login", data={"username": u1name, "password": "TEST123"})["access_token"]
    t2 = req("POST", "/api/auth/login", data={"username": u2name, "password": "TEST123"})["access_token"]

    tmp = Path(tempfile.gettempdir())
    def make_img(name: str) -> str:
        p = tmp / name
        img = Image.new("RGB", (140, 90), (random.randint(0, 255), random.randint(0, 255), random.randint(0, 255)))
        d = ImageDraw.Draw(img)
        d.text((20, 35), name[:12], fill=(255, 255, 255))
        img.save(p)
        return str(p)

    f1 = make_img(f"vis_{tag}_u1.png")
    f2 = make_img(f"vis_{tag}_u2.png")
    fa = make_img(f"vis_{tag}_admin.png")

    up1 = req("POST", "/api/upload", token=t1, files={"file": f1})
    up2 = req("POST", "/api/upload", token=t2, files={"file": f2})
    upa = req("POST", "/api/upload", token=at, files={"file": fa})
    check("uploads ok", up1.get("decision") in ("stored", "stored_shared") and up2.get("decision") in ("stored", "stored_shared"))

    # --- User1: only own data ---
    me1 = req("GET", "/api/me/events?limit=100", token=t1)
    names1 = {e["original_name"] for e in me1}
    check("user1 sees own file", Path(f1).name in names1)
    check("user1 does NOT see user2 file", Path(f2).name not in names1)
    check("user1 does NOT see admin file", Path(fa).name not in names1)
    check("user1 events only own user_id", all(e.get("user_id") == c1["id"] for e in me1))

    s1 = req("GET", "/api/me/stats", token=t1)
    check("user1 stats scoped", s1["total_upload_attempts"] == len(me1))

    # --- User2 blocked from admin APIs ---
    for path in ("/api/stats", "/api/events", "/api/admin/users", "/api/files"):
        try:
            req("GET", path, token=t2)
            check(f"user2 blocked from {path}", False)
        except RuntimeError as e:
            check(f"user2 blocked from {path}", "403" in str(e) or "401" in str(e))

    # --- Admin: sees everyone ---
    all_ev = req("GET", "/api/events?limit=200", token=at)
    all_names = {e["original_name"] for e in all_ev}
    check("admin sees user1 file", Path(f1).name in all_names)
    check("admin sees user2 file", Path(f2).name in all_names)
    check("admin sees own file", Path(fa).name in all_names)

    users_in_events = {e.get("username") for e in all_ev if e.get("original_name") in {Path(f1).name, Path(f2).name, Path(fa).name}}
    check("admin events include multiple users", u1name in users_in_events and u2name in users_in_events)

    filt = req("GET", f"/api/events?limit=50&user_id={c1['id']}", token=at)
    check("admin filter user1 only", all(e.get("user_id") == c1["id"] for e in filt) and Path(f1).name in {e["original_name"] for e in filt})
    check("admin filter excludes user2", Path(f2).name not in {e["original_name"] for e in filt})

    admin_stats = req("GET", "/api/stats", token=at)
    check("admin global stats >= 3 attempts", admin_stats["total_upload_attempts"] >= 3)

    # Admin /me still own-only (portal behavior)
    admin_me = req("GET", "/api/me/events?limit=100", token=at)
    check("admin /me is own-only", all(e.get("user_id") == admin_id for e in admin_me))

    # cleanup
    req("DELETE", f"/api/admin/users/{c1['id']}", token=at)
    req("DELETE", f"/api/admin/users/{c2['id']}", token=at)

    print()
    print(f"Result: {ok} passed, {fail} failed")
    return 1 if fail else 0


if __name__ == "__main__":
    sys.exit(main())
