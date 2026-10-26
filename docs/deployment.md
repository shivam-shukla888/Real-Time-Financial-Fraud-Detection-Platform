# Deployment Guide & Runtime Operations

This guide provides instructions for running the Real-Time Financial Fraud Detection Platform locally, via Docker Compose, and on cloud hosting platforms.

---

## 1. Local Development (Windows Laptop / CPU Fallback)

### Prerequisites
- Python 3.11+ (Python 3.14 compatible)
- Node.js v20+ (Node v24 tested)
- Git (optional)

### Step 1: Install Python Dependencies
```powershell
pip install -r requirements.txt
```

### Step 2: Prepare Data & Train Model
```powershell
# 1. Generate deterministic synthetic transactions dataset (seed=42)
python scripts/prepare_data.py --count 6000

# 2. Verify schema compliance and event monotonicity
python scripts/verify_data.py

# 3. Train imbalanced XGBoost model & log to MLflow
python scripts/train_model.py
```

### Step 3: Run the FastAPI Scoring Backend
```powershell
uvicorn app.api.main:app --host 127.0.0.1 --port 8010 --reload
```
API docs will be live at `http://127.0.0.1:8010/docs`.

### Step 4: Run the React + Vite Dashboard
In a separate PowerShell terminal:
```powershell
cd frontend
npm run dev
```
Open your browser at `http://localhost:5173`.

---

## 2. Docker & Container Packaging

### Port Configuration & Isolation
To prevent port collisions with other running projects (such as your existing AI Medical Imaging platform on ports 8000 and 8501):
- **Fraud API**: Port `8010`
- **Fraud Dashboard**: Port `5173`
- **Optional Kafka Broker**: Port `9092`

### Run with Docker Compose (Default Local Queue Mode)
```bash
docker compose up --build
```
This starts:
1. `fraud-api` on `http://localhost:8010`
2. `fraud-dashboard` on `http://localhost:5173`

### Run with Optional Apache Kafka Broker
To spin up the external streaming broker (Redpanda Kafka engine):
```bash
docker compose --profile kafka up --build
```

### Stopping Services
```bash
docker compose down
```

---

## 3. Accessible Cloud Deployment Options

### Option A: Railway or Render (Free / Low-Cost Tier)
1. Fork or push repository to GitHub.
2. Link repository to Railway or Render:
   - **Backend Web Service**:
     - Root directory: `./`
     - Build command: `pip install -r requirements.txt && python scripts/prepare_data.py && python scripts/train_model.py`
     - Start command: `uvicorn app.api.main:app --host 0.0.0.0 --port $PORT`
   - **Frontend Static Site**:
     - Root directory: `./frontend`
     - Build command: `npm install && npm run build`
     - Publish directory: `dist`
     - Add environment variable `VITE_API_URL` pointing to the deployed backend URL.

### Option B: Single VM (AWS EC2 t3.medium or DigitalOcean Droplet)
- CPU: 2 vCPUs
- RAM: 4 GB
- Run `docker compose up -d`
- Set up Nginx reverse proxy with Let's Encrypt SSL.
