# VPS deployment

## One-time Oracle VPS setup

Use the same account configured in the GitHub Actions VPS_USER secret.

```bash
cd ~
git clone https://github.com/wroxtaaar/Agentic-AI.git Agentic-AI
cd Agentic-AI
cp .env.example .env
nano .env
```

Configure at least:

- AGENT_API_TOKEN
- OPENROUTER_API_KEY
- AGENT_WORKSPACE_ROOTS

The repository's Docker Compose file mounts the VPS workspace and Docker socket because the agent is intended to inspect and manage trusted VPS projects.

## First start

Make sure Docker Compose is available, then:

```bash
cd ~/Agentic-AI
docker compose build
docker compose up -d
docker compose ps
curl http://127.0.0.1:8787/health
```

Expected health response:

```json
{"status":"ok","service":"oracle-vps-agent","version":"1.0.0"}
```

Agent memory is stored in the persistent agentic-data Docker volume.

## Automatic deployment

Every push to main triggers .github/workflows/deploy.yml.

The workflow:

1. SSHs into the VPS.
2. Updates the checkout to origin/main.
3. Validates the Compose configuration.
4. Builds the Docker image.
5. Runs syntax checks and tests inside the image.
6. Starts/recreates the Compose stack.
7. Waits for /health.

The required GitHub Actions secrets are:

- VPS_HOST
- VPS_USER
- VPS_SSH_KEY

No Python virtual environment or systemd service is required for deployment.

## Useful commands

```bash
cd ~/Agentic-AI
docker compose ps
docker compose logs -f agent
docker compose restart agent
docker compose up -d --build
docker compose down
```

## Private access

Port 8787 is bound to 127.0.0.1, so it is not exposed directly to the internet. Prefer Tailscale or another authenticated private access layer if you want to access the web UI/API remotely.
