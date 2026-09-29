"""Negative upload validation: ZIP, unsupported types, corrupted files."""
from __future__ import annotations

import json
import random
import string
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request
import zipfile
from pathlib import Path

from PIL import Image

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


def req(method, path, token=None, data=None, files=None, expect_error=False):
    url = BASE + path
    if files:
        cmd = ["curl", "-s", "-w", "\n%{http_code}", "-X", method, url]
        if token:
            cmd += ["-H", f"Authorization: Bearer {token}"]
        for key, fpath in files.items():
            cmd += ["-F", f"{key}=@{fpath}"]
        out = subprocess.check_output(cmd).decode("utf-8", errors="replace")
        body, _, code = out.rpartition("\n")
        code = code.strip()
        if expect_error:
            return int(code), body
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
        if expect_error:
            return e.code, raw
        raise RuntimeError(f"{method} {path} -> {e.code}: {raw}") from e


def detail_of(body: str) -> str:
    try:
        j = json.loads(body)
        d = j.get("detail", body)
        return d if isinstance(d, str) else str(d)
    except Exception:
        return body


def main() -> int:
    tag = "".join(random.choices(string.ascii_lowercase, k=6))
    tmp = Path(tempfile.gettempdir())

    admin = req("POST", "/api/auth/login", data={"username": "admin", "password": "ADMIN123"})
    at = admin["access_token"]
    u = f"val{tag}"
    created = req(
        "POST",
        "/api/admin/users",
        token=at,
        data={"username": u, "password": "TEST123", "role": "user"},
    )
    token = req("POST", "/api/auth/login", data={"username": u, "password": "TEST123"})["access_token"]

    # --- ZIP ---
    zpath = tmp / f"bad_{tag}.zip"
    with zipfile.ZipFile(zpath, "w") as zf:
        zf.writestr("hello.txt", "not allowed")
    code, body = req("POST", "/api/upload", token=token, files={"file": str(zpath)}, expect_error=True)
    msg = detail_of(body)
    check("zip rejected HTTP 400", code == 400, f"code={code} {msg}")
    check("zip message mentions archive/ZIP", "ZIP" in msg or "archive" in msg.lower(), msg)

    # --- Unsupported (.exe, .txt) ---
    exe = tmp / f"bad_{tag}.exe"
    exe.write_bytes(b"MZ" + b"\x00" * 32)
    code, body = req("POST", "/api/upload", token=token, files={"file": str(exe)}, expect_error=True)
    msg = detail_of(body)
    check("exe rejected", code == 400 and "Unsupported" in msg, msg)

    txt = tmp / f"bad_{tag}.txt"
    txt.write_text("plain text", encoding="utf-8")
    code, body = req("POST", "/api/upload", token=token, files={"file": str(txt)}, expect_error=True)
    msg = detail_of(body)
    check("txt rejected", code == 400 and "Unsupported" in msg, msg)

    # --- Corrupted image (wrong bytes, .png name) ---
    bad_png = tmp / f"corrupt_{tag}.png"
    bad_png.write_bytes(b"this is not a png file at all")
    code, body = req("POST", "/api/upload", token=token, files={"file": str(bad_png)}, expect_error=True)
    msg = detail_of(body)
    check("corrupt png rejected", code == 400, f"code={code} {msg}")
    check("corrupt png message", "Corrupt" in msg or "unreadable" in msg.lower(), msg)

    # --- Corrupted PDF ---
    bad_pdf = tmp / f"corrupt_{tag}.pdf"
    bad_pdf.write_bytes(b"%PDF-1.4\n% truncated garbage not a real pdf")
    code, body = req("POST", "/api/upload", token=token, files={"file": str(bad_pdf)}, expect_error=True)
    msg = detail_of(body)
    check("corrupt pdf rejected", code == 400, f"code={code} {msg}")
    check("corrupt pdf message", "Corrupt" in msg or "unreadable" in msg.lower() or "PDF" in msg, msg)

    # --- ZIP renamed as .docx (archive without Word parts) ---
    fake_docx = tmp / f"fake_{tag}.docx"
    with zipfile.ZipFile(fake_docx, "w") as zf:
        zf.writestr("readme.txt", "not a word doc")
    code, body = req("POST", "/api/upload", token=token, files={"file": str(fake_docx)}, expect_error=True)
    msg = detail_of(body)
    check("fake docx (zip) rejected", code == 400, f"code={code} {msg}")
    check(
        "fake docx message",
        "Corrupt" in msg or "unreadable" in msg.lower() or "Word" in msg,
        msg,
    )

    # --- Valid image still accepted (no regression) ---
    good = tmp / f"good_{tag}.png"
    Image.new("RGB", (64, 64), (10, 20, 200)).save(good)
    up = req("POST", "/api/upload", token=token, files={"file": str(good)})
    check("valid png still stored", up.get("decision") in ("stored", "stored_shared"), str(up.get("decision")))

    # Invalid uploads must not appear as stored events
    me = req("GET", "/api/me/events?limit=50", token=token)
    names = {e["original_name"] for e in me if e["decision"] in ("stored", "stored_shared")}
    check("zip not in stored events", zpath.name not in names)
    check("corrupt png not stored", bad_png.name not in names)
    check("valid png in stored events", good.name in names)

    req("DELETE", f"/api/admin/users/{created['id']}", token=at)
    check("cleanup user", True)

    print()
    print(f"Result: {ok} passed, {fail} failed")
    return 1 if fail else 0


if __name__ == "__main__":
    sys.exit(main())
