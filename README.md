# Oracle VPS Agent

A self-hosted multi-agent engineering control plane for managing software projects and services on an Oracle VPS.

## Agent team

- **Orchestrator** — routes requests to the right specialist and coordinates multi-step work.
- **Project Agent** — discovers repositories and project structure.
- **Coding Agent** — diagnoses source problems and creates exact approval-gated patches.
- **DevOps Agent** — investigates Docker, services and resource state.
- **Git Agent** — reads branches, commits, history and diffs.
- **Debugger Agent** — correlates logs, source and configuration.
- **Security Agent** — reviews proposed operations for secrets and unsafe scope.
- **Verification Agent** — runs post-change checks.
- **Memory Agent** — stores durable non-secret project facts.

Specialists are routed by the orchestrator and operate through a shared, approval-aware tool layer. Read-only investigation is automatic; mutations are represented as durable approval records and executed only after explicit approval. Docker actions include post-action verification.

## Safety model

Read operations are available automatically. State-changing operations require an approval record. Source patches record exact old_text, new_text, target paths and SHA-256 snapshots. Applying a patch requires the snapshot to still match and creates a backup first.

Container restarts also require approval. The generic shell is allowlisted and read-only. Docker and Git use dedicated tools. Sensitive files are blocked or redacted.

## VPS setup

```bash
git clone https://github.com/wroxtaaar/Agentic-AI.git
cd Agentic-AI
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
nano .env
python -m uvicorn app:app --host 127.0.0.1 --port 8787
```

Recommended .env values:

```env
AI_PROVIDER=openrouter
OPENROUTER_API_KEY=...
OPENROUTER_MODEL=openrouter/free
AGENT_API_TOKEN=generate-a-long-random-token
AGENT_WORKSPACE_ROOTS=/home/ubuntu
```

Use Tailscale or another private network for access. Do not expose the raw control API publicly.

## API

- GET /health
- GET /api/status
- POST /api/chat
- GET /api/approvals
- POST /api/approvals/{id}/approve
- POST /api/approvals/{id}/reject
- POST /api/proposals/{id}/approve
- POST /api/proposals/{id}/apply
- POST /api/actions/{id}/execute — executes any approved supported action
- POST /api/actions/docker/{id}/execute — backward-compatible Docker executor
- POST /api/actions/restart-container — legacy restart proposal endpoint

## Example tasks

- Check all my projects and tell me which ones look unhealthy.
- Investigate why torrent-studio is failing.
- Fix the crash in FinanceSMSTracker and prepare a patch.
- Check Docker containers and find anything using too much memory.

The agent investigates first, presents evidence, and requires approval before mutations. Docker start/restart/stop, Git commits, durable memory writes, and exact source patches are approval-gated. Approved Docker actions are verified after execution. The control plane is intended to remain private behind Tailscale or another trusted network.
