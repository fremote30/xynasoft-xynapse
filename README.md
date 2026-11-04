# Xynasoft Xynapse
Regulated AI brain platform (MVP).
# xynasoft-xynapse

## Run locally / Codespaces

1) Start Postgres
docker compose up -d

2) Create venv + install
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

3) Init DB
python -m storage.init_db

4) Run API
python -m uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload

## Auth
Send header:
X-API-Key: <API_KEY from .env>
