# AI4INSURANCE Backend + Frontend

## Backend (Flask API + Pipeline)

1. Create and activate a virtual environment:
   
   ```bash
   python3 -m venv backend/venv
   backend/venv/bin/pip install --upgrade pip setuptools wheel
   backend/venv/bin/pip install flask pandas numpy requests
   ```

2. Run the backend (this executes the pipeline and starts the server):
   
   ```bash
   backend/venv/bin/python backend/comined/main.py
   ```

   - API endpoint: `http://127.0.0.1:5000/api/decisions`
   - HTML viewer (optional): `http://127.0.0.1:5000/`

Note: The calculator may attempt FX conversion via OANDA and fall back to `NaN` if the API is unavailable; the rest of the pipeline continues.

## Frontend (Static)

Open `frontend/index.html` in a browser. By default it fetches from `http://127.0.0.1:5000/api/decisions`.

To point to a different backend URL, use:

```text
frontend/index.html?api=http://localhost:5000/api/decisions
```

Ensure the backend is running first. 