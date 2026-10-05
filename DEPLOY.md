# VPS deployment

## Install on Oracle VPS

```bash
cd ~
git clone https://github.com/wroxtaaar/Agentic-AI.git
cd Agentic-AI
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python - <<'PY'
import secrets
print(secrets.token_urlsafe(48))
PY
nano .env
```

Set the generated value as AGENT_API_TOKEN, your OpenRouter key as OPENROUTER_API_KEY, and configure AGENT_WORKSPACE_ROOTS.

## Start

```bash
source .venv/bin/activate
python -m uvicorn app:app --host 127.0.0.1 --port 8787
curl http://127.0.0.1:8787/health
```

For persistent operation, use the supplied systemd service example.

## Private access

Prefer Tailscale rather than opening port 8787 publicly. The systemd example binds to localhost.
