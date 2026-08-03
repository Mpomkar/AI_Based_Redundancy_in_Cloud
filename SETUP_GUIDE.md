# AI-Based Cloud Redundancy Prediction System — Setup Guide

**Version:** 1.0  
**Repository:** https://github.com/Mpomkar/AI_Based_Redundancy_in_Cloud

This guide walks team members through installing and running the project from scratch on **Windows**, **macOS**, or **Linux**.

---

## Table of contents

1. [What you are setting up](#1-what-you-are-setting-up)
2. [System requirements](#2-system-requirements)
3. [Get the project](#3-get-the-project)
4. [One-time setup (automated)](#4-one-time-setup-automated)
5. [One-time setup (manual)](#5-one-time-setup-manual)
6. [Running the application](#6-running-the-application)
7. [Verify installation](#7-verify-installation)
8. [Login credentials](#8-login-credentials)
9. [Optional configuration](#9-optional-configuration)
10. [Troubleshooting](#10-troubleshooting)
11. [Project structure](#11-project-structure)
12. [Daily workflow for developers](#12-daily-workflow-for-developers)

---

## 1. What you are setting up

This is a **full-stack web application** with two parts that must run **at the same time**:

| Component | Technology | Default URL | Purpose |
|-----------|------------|-------------|---------|
| **Backend** | Python, FastAPI | http://127.0.0.1:8000 | API, file processing, ML model |
| **Frontend** | React, Vite | http://localhost:5173 | Dashboard UI |

The frontend proxies API calls to the backend. If the backend is not running, uploads and dashboard data will fail (500 errors).

---

## 2. System requirements

### Required software

| Software | Minimum version | Download |
|----------|-----------------|----------|
| **Python** | 3.10+ | https://www.python.org/downloads/ |
| **Node.js** | 18+ (includes npm) | https://nodejs.org/ |

### Windows notes

- During Python install, check **“Add python.exe to PATH”**.
- Use **PowerShell** or **Command Prompt** for commands below.
- If `npm` fails with “running scripts is disabled”, use our setup scripts (they handle this) or run:
  ```powershell
  Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
  ```

### Disk space

- ~500 MB for Python packages and `node_modules` (first install).

### Ports used

| Port | Service |
|------|---------|
| 8000 | Backend API |
| 5173 | Frontend (Vite; may use 5174 if 5173 is busy) |

Ensure these ports are free or change them (see Troubleshooting).

---

## 3. Get the project

### Option A — Clone from GitHub

```powershell
git clone https://github.com/Mpomkar/AI_Based_Redundancy_in_Cloud.git
cd AI_Based_Redundancy_in_Cloud
```

### Option B — Download ZIP

1. Download the repository ZIP from GitHub.
2. Extract to a folder, e.g. `C:\Projects\AI_Based_Redundancy_in_Cloud`.
3. Open a terminal in that folder.

---

## 4. One-time setup (automated)

Run **once** per machine after cloning the repo.

### Windows (recommended)

**PowerShell** (from project root):

```powershell
.\scripts\setup.ps1
```

Or double-click:

- `scripts\setup.bat` — installs dependencies only
- `scripts\start-all.bat` — runs setup if needed, then starts both servers

What `setup.ps1` does:

1. Checks Python 3.10+ and Node.js
2. Creates `backend\.venv` (Python virtual environment)
3. Installs Python packages from `requirements.txt`
4. Runs `npm install` in `frontend\`
5. Verifies backend imports

**Expected time:** 2–5 minutes (depends on network).

### macOS / Linux

```bash
chmod +x scripts/*.sh
./scripts/setup.sh
```

---

## 5. One-time setup (manual)

Use this if automated scripts fail or you prefer manual steps.

### 5.1 Backend

```powershell
cd backend
python -m venv .venv
```

**Windows — activate venv:**

```powershell
.\.venv\Scripts\Activate.ps1
```

**macOS/Linux:**

```bash
source .venv/bin/activate
```

**Install dependencies** (from `backend` folder):

```powershell
pip install -r ..\requirements.txt
```

**Verify:**

```powershell
python -c "from app.main import app; print('OK')"
```

### 5.2 Frontend

```powershell
cd frontend
npm install
```

Use `npm.cmd install` on Windows if PowerShell blocks `npm`.

---

## 6. Running the application

You need **two terminals** (or use `start-all`).

### Windows — start both servers

```powershell
.\scripts\start-all.ps1
```

This opens two PowerShell windows (backend + frontend).

### Windows — separate terminals

**Terminal 1 — Backend:**

```powershell
.\scripts\start-backend.ps1
```

**Terminal 2 — Frontend:**

```powershell
.\scripts\start-frontend.ps1
```

### macOS / Linux

**Terminal 1:**

```bash
./scripts/start-backend.sh
```

**Terminal 2:**

```bash
./scripts/start-frontend.sh
```

### Manual start commands

**Backend** (from `backend` folder, venv active):

```powershell
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

**Frontend** (from `frontend` folder):

```powershell
npm run dev
```

### Open the app

1. Browser: **http://localhost:5173** (or the port shown in the Vite terminal, e.g. 5174)
2. Login page: **http://localhost:5173/login**

---

## 7. Verify installation

### Backend health check

Open in browser or run:

```powershell
curl http://127.0.0.1:8000/api/health
```

Expected:

```json
{"status":"ok","service":"Cloud Redundancy AI"}
```

API documentation: http://127.0.0.1:8000/docs

### Frontend check

- Dashboard loads without a red “Error” banner at the top.
- Stats show zeros initially (no uploads yet).

### Upload test

1. Log in (see below).
2. Upload a **PDF**, **DOCX**, or **image** (JPEG/PNG).
3. File should process — stored or rejected with analysis, not a 500 error.

---

## 8. Login credentials

| Field | Value |
|-------|-------|
| **Username** | `admin` (case-insensitive) |
| **Password** | `ADMIN123` (case-sensitive) |

This is a **demo client-side login** (stored in browser `localStorage`). It is not connected to the backend API.

---

## 9. Optional configuration

Copy the example env file:

```powershell
copy backend\.env.example backend\.env
```

Edit `backend\.env`:

```env
CONTENT_MATCH_REJECT_THRESHOLD_PERCENT=92
```

| Variable | Default | Description |
|----------|---------|-------------|
| `CONTENT_MATCH_REJECT_THRESHOLD_PERCENT` | 92 | Reject when content match ≥ this % |
| `REDUNDANT_THRESHOLD` | 0.62 | ML probability threshold (with similarity rules) |
| `MAX_PDF_TEXT_CHARS` | 120000 | Max text extracted from documents |

Restart the backend after changing `.env`.

---

## 10. Troubleshooting

### `npm` — “running scripts is disabled” (Windows PowerShell)

**Fix A** — use setup scripts (they use `npm.cmd`).

**Fix B** — current session only:

```powershell
Set-ExecutionPolicy -ExecutionPolicy Bypass -Scope Process
```

**Fix C** — permanent for your user:

```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### `'vite' is not recognized` or upload 500 error

**Cause:** Frontend dependencies not installed, or backend not running.

**Fix:**

```powershell
.\scripts\setup.ps1
.\scripts\start-all.ps1
```

### `Could not read package.json` when running `npm run dev`

**Cause:** Running npm from project **root** instead of `frontend`.

**Fix:** Run from `frontend` or use `.\scripts\start-frontend.ps1`.

### Port 5173 already in use

Vite automatically tries the next port (e.g. **5174**). Use the URL shown in the terminal.

### Port 8000 already in use

Stop the other process or change the backend port:

```powershell
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8001
```

Then update `frontend/vite.config.ts` proxy target to `http://127.0.0.1:8001`.

### Python import errors / wrong Python

Use the venv Python explicitly:

```powershell
backend\.venv\Scripts\python.exe -m pip install -r requirements.txt
backend\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

### `pip install` fails on Windows

- Ensure Python 3.10+ (not 3.7/3.8).
- Upgrade pip: `python -m pip install --upgrade pip`
- Use the venv’s `python.exe`, not the Windows Store stub.

### Dashboard shows “Error” with empty stats

Backend is down. Start backend first, then refresh the page.

### Supported upload file types

| Supported | Not supported |
|-----------|----------------|
| PDF, DOCX | .txt, .xlsx, .zip |
| JPEG, PNG, WebP, GIF | Other formats |

---

## 11. Project structure

```
AI_Based_Redundancy_in_Cloud/
├── backend/
│   ├── app/                 # FastAPI application
│   │   ├── main.py          # API routes
│   │   ├── services/        # Upload pipeline, ML, similarity
│   │   └── ...
│   ├── .venv/               # Python virtual env (created by setup)
│   ├── storage/             # Uploaded files (created at runtime)
│   ├── models/              # ML model (auto-created at first run)
│   └── .env.example         # Optional config template
├── frontend/
│   ├── src/                 # React UI
│   ├── package.json
│   └── vite.config.ts       # Dev server + API proxy
├── scripts/
│   ├── setup.ps1 / setup.sh # One-time setup
│   ├── start-all.ps1        # Start both servers (Windows)
│   └── ...
├── docs/                    # Diagrams for README
├── requirements.txt         # Python dependencies
├── SETUP_GUIDE.md           # This file
├── docs/SETUP_GUIDE.html    # Printable / PDF version
└── README.md                # Project overview + How AI Works
```

---

## 12. Daily workflow for developers

After the **one-time setup**, each day you only need to start the servers:

```powershell
.\scripts\start-all.ps1
```

Or start backend and frontend manually in two terminals.

**Stop servers:** Close the terminal windows or press `Ctrl+C` in each.

**Re-setup** (only if dependencies change):

```powershell
.\scripts\setup.ps1
```

---

## Quick reference card

| Step | Command (Windows) |
|------|-------------------|
| First-time setup | `.\scripts\setup.ps1` |
| Start everything | `.\scripts\start-all.ps1` |
| App URL | http://localhost:5173 |
| API URL | http://127.0.0.1:8000 |
| API docs | http://127.0.0.1:8000/docs |
| Login | admin / ADMIN123 |
| AI documentation | README.md → “How AI Works” |

---

## Export this guide as PDF

1. Open `docs/SETUP_GUIDE.html` in Chrome or Edge.
2. Press `Ctrl+P` (Print).
3. Destination: **Save as PDF**.
4. Save as `SETUP_GUIDE.pdf`.

---

*For AI pipeline details, see README.md section “How AI Works”.*
