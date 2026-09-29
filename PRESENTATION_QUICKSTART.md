# Presentation Quick Start (for teammates)

Share this file with anyone presenting tomorrow.

## Requirements

- Python 3.10+
- Node.js 18+

## Run (Windows)

From the project root folder `Final-Project-main`:

```powershell
.\scripts\setup.ps1
.\scripts\start-all.ps1
```

Or manually in **two** terminals:

**Terminal 1 — Backend** (listens on all interfaces for LAN sharing)

```powershell
cd backend
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**Terminal 2 — Frontend**

```powershell
cd frontend
npm install
npm run dev -- --host
```

Open: **http://localhost:5173** (or the LAN URL printed in the terminal)

## Login accounts

| Role | Username | Password | Goes to |
|------|----------|----------|---------|
| Admin | `admin` | `ADMIN123` | `/admin` dashboard + Manage Users |
| Demo user | `user` | `USER123` | `/portal` (own files only) |

Username is case-insensitive (`Admin` works). Password is case-sensitive.

## Same admin on two PCs (shared files)

**Why it looked broken:** each PC that runs its own backend gets a **separate** `backend/app.db`. Same login (`admin`) exists on both, but uploads are **not** shared.

**Correct setup — one shared backend:**

1. Run `.\scripts\start-all.ps1` on **PC-A only**.
2. Note the **LAN** URL printed (example: `http://192.168.1.10:5173`).
3. On **PC-B**, open that LAN URL in the browser (do **not** start another backend).
4. Login as `admin` / `ADMIN123` — uploads from either PC appear for everyone using PC-A’s server.

**Where files are saved:** accepted uploads are written on the **backend PC** under Desktop → **Uploaded Files** → `uploads` → `<user_id>`. Other PCs do not get a local copy; they see the same files through PC-A’s shared backend.

Optional: if PC-B must run its own Vite, set `frontend/.env`:

```env
VITE_API_BASE=http://192.168.1.10:8000
```

then `npm run dev` on PC-B (pointing at PC-A’s API).

Allow Windows Firewall for ports **8000** and **5173** on PC-A if LAN access fails.

## Demo script (2–3 minutes)

1. Login as **admin** → show global File Status, charts, Manage Users.
2. Create a new user (optional) or use `user` / `USER123`.
3. Logout → login as **user** → show User Portal (only their data).
4. Upload a PDF/DOCX/image as **user** → show analysis.
5. Upload the **same file again** as the same user → exact duplicate **blocked** (toast).
6. Logout → login as **admin** (or another user) → upload the **same file with a different name** → it is **stored as 0 KB shared** (toast), not blocked.
7. Admin dashboard → filter by user → see "Stored 0 KB" / Shared action.

## Important

- Backend must run on port **8000** and frontend on **5173**.
- Opening `http://127.0.0.1:8000` in the browser alone is the API — use `/docs` for API docs, or the frontend URL for the UI.
- Supported uploads: PDF, Word (.docx), JPEG/PNG/WebP/GIF.

## If login fails with Not Found

An old backend is running. Stop it and restart from the `backend` folder (see above).
