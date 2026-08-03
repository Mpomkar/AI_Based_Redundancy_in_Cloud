# AI-Based Redundancy Prediction and Optimization (Cloud Storage Demo)

Full-stack demo: **FastAPI** backend (SHA-256 dedup, PDF + **Word (.docx)** text, image pHash similarity, configurable **policy threshold** %, scikit-learn classifier, risk score, unified-diff **guidance**) and **React + Vite** dashboard.

## Prerequisites

- Python 3.10+
- Node.js 18+

## Backend

Use the **same Python** you used for `pip` (on Windows, `where python` may point to a stub; if imports fail, run with `py -3.14` or your venv’s `python.exe`).

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r ..\requirements.txt
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

API: `http://127.0.0.1:8000` — OpenAPI docs: `/docs`

## Frontend

```powershell
cd frontend
npm install
npm run dev
```

Open `http://127.0.0.1:5173` (Vite proxies `/api` to the backend).

## What it does

1. **Exact duplicate** — same SHA-256 as a stored file → rejected.
2. **Similarity** — PDFs & DOCX: word-level **Jaccard** vs stored text (one pool); images: perceptual hash distance.
3. **Policy threshold** — reject when best match **≥ `content_match_reject_threshold_percent`** (default **92**). Override in `.env`, e.g. `CONTENT_MATCH_REJECT_THRESHOLD_PERCENT=88`.
4. **Guidance** — API returns **content match %**, **reference filename**, and a **unified-diff excerpt** vs that file (standard `difflib` pattern).
5. **Features** — max similarity, size ratio vs best match, neighbor count → ML.
6. **ML** — logistic regression predicts redundancy probability; combined with policy for the final decision.
7. **Risk** — 0–100% for the dashboard; all attempts logged.

## Project layout

- `backend/app/` — API, DB models, processing pipeline
- `frontend/` — dashboard UI


<img width="1683" height="1099" alt="image" src="https://github.com/user-attachments/assets/3dcd3019-652b-4e7b-b896-de34c74c086d" />
<img width="1688" height="1097" alt="image" src="https://github.com/user-attachments/assets/68f45eb6-6261-461a-9308-eee6752461cf" />
<img width="1683" height="1095" alt="image" src="https://github.com/user-attachments/assets/0739837b-9dbf-4896-9e4a-7b9280c94dfb" />


