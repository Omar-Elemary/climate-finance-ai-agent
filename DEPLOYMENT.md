# Deployment & Operations Guide

## 1. Local Development (Without Docker)

### Prerequisites
- Python 3.11+
- Virtual environment activated

### Installation & Run
```bash
pip install -r requirements.txt
pip install -r backend/requirements.txt
uvicorn backend.app.main:app --reload --port 8000
