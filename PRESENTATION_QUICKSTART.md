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

**Terminal 1 — Backend**

```powershell
cd backend
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

**Terminal 2 — Frontend**

```powershell
cd frontend
npm install
npm run dev
```

Open: **http://localhost:5173**

## Login accounts

| Role | Username | Password | Goes to |
|------|----------|----------|---------|
| Admin | `admin` | `ADMIN123` | `/admin` dashboard + Manage Users |
| Demo user | `user` | `USER123` | `/portal` (own files only) |

Username is case-insensitive (`Admin` works). Password is case-sensitive.

## Demo script (2–3 minutes)

1. Login as **admin** → show global File Status, charts, Manage Users.
2. Create a new user (optional) or use `user` / `USER123`.
3. Logout → login as **user** → show User Portal (only their data).
4. Upload a PDF/DOCX/image as **user** → show analysis.
5. Upload the **same file again** as the same user → exact duplicate **blocked** (toast).
6. Logout → login as **admin** (or another user) → upload the **same file with a different name** → it is **stored as 0 KB shared** (toast), not blocked.
7. Admin dashboard → filter by user → see “Stored 0 KB” / Shared action.

## Important

- Backend must run on port **8000** and frontend on **5173**.
- Opening `http://127.0.0.1:8000` in the browser shows 404 — that is normal (API only). Use `/docs` for API docs.
- Supported uploads: PDF, Word (.docx), JPEG/PNG/WebP/GIF.

## If login fails with Not Found

An old backend is running. Stop it and restart from the `backend` folder (see above).
