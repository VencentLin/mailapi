# MailAPI

MailAPI is an Outlook OAuth2 verification-code mail retrieval platform.

## Phase 1 Local Checks

Install backend dependencies:

```bash
pip install -e ".[dev]"
```

Run backend tests:

```bash
pytest tests/backend -v
ruff check backend tests/backend
```

Build frontend:

```bash
cd frontend
npm install
npm run build
```

Build Docker image:

```bash
docker build -t mailapi:phase1 .
```

Run container:

```bash
docker run --rm -p 8000:8000 --env-file .env mailapi:phase1
```

Open:

- `http://localhost:8000/api/health`
- `http://localhost:8000/`
