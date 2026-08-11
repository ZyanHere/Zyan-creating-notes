# Agent Application

This directory contains the future `agent` application for the project.

Its responsibility will be the AI-side application logic, including the planning and generation workflows that turn user learning needs into structured educational outputs.

This repository is expected to grow into three separate top-level applications:

- `agent/` for AI planning and generation logic
- `frontend/` for the user-facing client
- `backend/` for server-side application APIs and supporting services

This setup is intentionally minimal. It establishes a clean Python foundation without introducing product functionality, workflow orchestration, or application architecture prematurely.

## Environment Setup

Create the virtual environment:

```powershell
python -m venv .venv
```

Activate it in PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

Install dependencies:

```powershell
pip install -r requirements.txt
```

Create local environment variables:

```powershell
Copy-Item .env.example .env
```

## Current Dependency Choice

The initial setup includes only `python-dotenv` so the application can load local configuration cleanly once actual agent code is introduced.
