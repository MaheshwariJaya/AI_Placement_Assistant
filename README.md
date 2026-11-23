# AI-Powered Placement Intelligence System

[![Architecture: Modular Monolith](https://img.shields.io/badge/Architecture-Modular%20Monolith-indigo.svg)](docs/SYSTEM_ARCHITECTURE.md)
[![Backend: FastAPI](https://img.shields.io/badge/Backend-FastAPI-009688.svg)](https://fastapi.tiangolo.com/)
[![Frontend: React + Vite](https://img.shields.io/badge/Frontend-React%2018%20%2B%20Vite-61DAFB.svg)](https://vitejs.dev/)
[![Database: PostgreSQL](https://img.shields.io/badge/Database-PostgreSQL%2016-336791.svg)](https://www.postgresql.org/)
[![ORM: SQLAlchemy 2.0](https://img.shields.io/badge/ORM-SQLAlchemy%202.0%20Async-D71F00.svg)](https://www.sqlalchemy.org/)

An enterprise-grade, lightweight full-stack academic minor project designed to automate campus placements, resume parsing, deterministic academic eligibility verification, weighted skill compatibility scoring, and AI-assisted career coaching for collegiate institutions.

---

## 1. System Architecture Overview

The system strictly adheres to a **Modular Monolithic** pattern:
- **One React 18 Frontend:** TypeScript, Vite, Tailwind CSS, React Router v6, Recharts.
- **One FastAPI Backend:** Python 3.11+, Pydantic v2 Settings, SQLAlchemy 2.0 Async, Alembic Migrations.
- **One PostgreSQL Database:** 3NF relational schema with institutional multi-tenancy scoping.
- **Abstracted AI Engine:** Unified interface supporting **Google Gemini API**, **OpenAI API**, and an offline **Mock Provider** without silent fallbacks.
- **Local Document Parsers:** PyMuPDF (`fitz`) and `python-docx` for on-premise resume parsing with zero cloud OCR costs and strict privacy.

---

## 2. Project Directory Structure

```text
AI-Powered Placement Intelligence System/
├── backend/
│   ├── alembic/                      # Database migrations
│   │   ├── versions/                 # Version-controlled migration scripts
│   │   │   └── 001_initial_baseline.py
│   │   ├── env.py                    # Async migration runner
│   │   └── script.py.mako            # Migration template
│   ├── app/
│   │   ├── core/                     # Foundational infrastructure
│   │   │   ├── base.py               # DeclarativeBase, mixins
│   │   │   ├── database.py           # Async engine, sessionmaker, ping probe
│   │   │   └── errors.py             # Centralized JSON error handlers
│   │   ├── models/                   # Relational ORM models
│   │   │   ├── organization.py       # Institution, Department
│   │   │   └── user.py               # User (student, tpo, recruiter, admin)
│   │   ├── routes/                   # API Route controllers
│   │   │   └── health.py             # Liveness & readiness probes
│   │   ├── config.py                 # Pydantic Settings (.env reader)
│   │   └── main.py                   # FastAPI application factory
│   ├── tests/                        # Automated test suite
│   │   ├── test_alembic.py           # Offline DDL generation tests
│   │   ├── test_health.py            # API endpoint integration tests
│   │   └── test_imports.py           # Core dependency verification
│   ├── uploads/                      # Private local storage (Git excluded)
│   │   └── resumes/
│   ├── alembic.ini                   # Alembic configuration
│   └── requirements.txt              # Pinned backend dependencies
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── common/               # Button, Input, Card, Badge
│   │   │   └── layout/               # Navbar, Footer, DashboardLayout
│   │   ├── pages/
│   │   │   ├── dashboards/           # Student, TPO, Recruiter, Admin views
│   │   │   └── LandingPage.tsx       # Modern responsive landing view
│   │   ├── services/                 # Axios API clients
│   │   ├── types/                    # TypeScript interfaces
│   │   ├── App.tsx                   # React Router route registry
│   │   └── main.tsx                  # Application entry point
│   ├── package.json                  # Frontend dependencies
│   ├── tailwind.config.js            # Design system tokens
│   └── vite.config.ts                # Vite proxy configuration
├── docs/                             # Engineering Blueprints (Phase 0 & 1)
│   ├── SRS.md                        # Finalized requirements specification
│   ├── SYSTEM_ARCHITECTURE.md        # Architecture & component boundaries
│   ├── DATABASE_DESIGN.md            # ER diagram & schema dictionary
│   ├── API_SPECIFICATION.md          # REST API contracts
│   ├── UI_UX_PLAN.md                 # Design system & dashboard wireframes
│   ├── DEVELOPMENT_ROADMAP.md        # Phases 0 through 9 milestones
│   └── PROJECT_DECISIONS.md          # Architectural Decision Records (ADRs)
├── .env.example                      # Template configuration (committed)
├── .gitignore                        # Strict secrets & upload exclusions
└── README.md
```

---

## 3. Quickstart & Local Setup Guide (Windows PowerShell)

### Prerequisites
- Python 3.11 or 3.12 (Installed locally)
- Node.js v18+ and npm v9+
- PostgreSQL 15+ (Local instance on port 5432)

---

### Step 1: Clone and Configure Environment

```powershell
# Navigate to the workspace root
cd "D:\AI-Powered Placement Intelligence System"

# Copy the placeholder template to local .env
Copy-Item .env.example .env
```

*(Edit `.env` to set your local PostgreSQL password if different from the default).*

---

### Step 2: Backend Setup & Virtual Environment

```powershell
# Create Python virtual environment
py -3.12 -m venv backend\.venv
# (or: & "C:\Users\Owner\AppData\Local\Programs\Python\Python312\python.exe" -m venv backend\.venv)

# Activate virtual environment
.\backend\.venv\Scripts\Activate.ps1

# Install pinned dependencies
pip install -r backend/requirements.txt
```

---

### Step 3: Database Migrations (PostgreSQL)

Ensure PostgreSQL service is running and database `placement_db` exists:

```sql
-- In psql or pgAdmin:
CREATE DATABASE placement_db;
```

Run Alembic migrations to apply initial baseline tables (`institutions`, `departments`, `users`):

```powershell
$env:PYTHONPATH="backend"
alembic -c backend/alembic.ini upgrade head
```

*(To preview SQL without connecting to the database: `alembic -c backend/alembic.ini upgrade head --sql`)*

---

### Step 4: Frontend Setup

Open a new PowerShell terminal:

```powershell
cd "D:\AI-Powered Placement Intelligence System\frontend"

# Install npm packages
npm install

# Run frontend development server
npm run dev
```

The frontend SPA will be accessible at: **`http://localhost:5173`**

---

### Step 5: Start the Backend Server

```powershell
cd "D:\AI-Powered Placement Intelligence System"
$env:PYTHONPATH="backend"
.\backend\.venv\Scripts\python.exe -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000 --reload
```

- API Base: **`http://127.0.0.1:8000`**
- Interactive Swagger Documentation: **`http://127.0.0.1:8000/docs`**
- Liveness Probe: **`http://127.0.0.1:8000/health/live`**
- Readiness Probe: **`http://127.0.0.1:8000/health/ready`**

---

## 4. Running Automated Tests

Run the automated backend test suite using `pytest`:

```powershell
cd "D:\AI-Powered Placement Intelligence System"
$env:PYTHONPATH="backend"
.\backend\.venv\Scripts\pytest.exe backend/tests -v -o asyncio_mode=auto
```

Verify frontend production build:

```powershell
cd "D:\AI-Powered Placement Intelligence System\frontend"
npm run build
```

---

## 5. Security & Git Safety Rules

- `.env` and all credential files are strictly ignored by Git via `.gitignore`.
- Student uploaded resumes in `backend/uploads/resumes/` are strictly excluded from version control.
- API keys for Gemini and OpenAI are never hardcoded and resolve strictly from environment variables.
- Offline `AI_PROVIDER=mock` mode allows complete testing without consuming API credits or exposing keys.

