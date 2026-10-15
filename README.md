# Oracle VPS Agent

A self-hosted multi-agent engineering control plane for managing software projects and services on an Oracle VPS.

## Agent team

- **Architect** — plans work before execution and reviews the worker's report afterward.
- **Worker/orchestrator** — uses repository and VPS tools to investigate and produce exact patch proposals.
- **Specialists** — project discovery, coding, DevOps, Git, debugging, security, verification and memory.
- **Verification** — runs bounded project-aware syntax, test and build checks.

The architect, worker, and delegated specialists can use different model IDs or FreeLLMAPI fallback chains behind an OpenAI Chat Completions gateway. Specialists currently use the worker model chain. For coding tasks, the worker can create a detached Git worktree, edit files only inside that worktree, run bounded project-aware checks, repair failures, and submit a diff for approval. Applying the verified diff to the original checkout requires approval; committing and pushing remain separate approval-gated actions.

## Free model gateway (FreeLLMAPI)

The Docker stack runs [FreeLLMAPI](https://github.com/tashfeenahmed/freellmapi) as the local model gateway. Its dashboard/API is bound to VPS loopback at port 3001 and is not exposed publicly. The deploy workflow generates a persistent encryption key in the private VPS .env; do not rotate or delete it after provider keys have been saved.

1. When you can access the VPS, create an SSH tunnel: `ssh -L 3001:127.0.0.1:3001 <vps-user>@<vps-host>`. Keep that terminal/session open and visit `http://127.0.0.1:3001` on the same device.
2. Complete FreeLLMAPI first-run setup. If it asks for a setup code, retrieve it on the VPS with `cd ~/Agentic-AI && docker compose logs freellmapi`. Keep the dashboard credentials private.
3. Add provider API keys for providers whose free tiers you want to use. FreeLLMAPI is open-source/free software, but upstream provider quotas and terms apply.
4. Copy the unified API key from the dashboard. Put it in the VPS's private `~/Agentic-AI/.env` as `FREELLMAPI_API_KEY=...`. Then run `cd ~/Agentic-AI && docker compose up -d --force-recreate agent`.
5. Start with `auto` model selection. Check the live catalogue at `http://127.0.0.1:3001/v1/models` through the tunnel and choose exact model IDs for `ARCHITECT_MODEL` and `WORKER_MODEL` after verifying tool/function-calling support. Put those IDs in the VPS .env and recreate the agent.

The agent container overrides `OPENROUTER_API_KEY` with an empty value, so it will not silently fall back to a paid OpenRouter route. Until `FREELLMAPI_API_KEY` is configured and FreeLLMAPI has usable provider keys/models, agent model calls will fail rather than incur API charges. FreeLLMAPI routes/fails over only among providers and models configured in its dashboard; verify that each selected upstream is genuinely free before using it.

## Safety model

Read operations are available automatically. State-changing operations require an approval record. Source patches record exact old_text, new_text, target paths and SHA-256 snapshots. Applying a patch requires the snapshot to still match and creates a backup first.

Container restarts also require approval. The generic shell is allowlisted and read-only. Docker and Git use dedicated tools. Sensitive files are blocked or redacted. Verification commands are bounded and project-aware.

## VPS setup

The deployment workflow updates the existing checkout and runs Python syntax checks and unit tests before starting the stack. For a manual agent-only install:

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

Use Tailscale or another private network for agent access. Do not expose the raw control API publicly.

## API

- GET /health
- GET /api/status
- POST /api/chat
- GET /api/approvals
- POST /api/approvals/{id}/approve
- POST /api/approvals/{id}/reject
- POST /api/proposals/{id}/approve
- POST /api/proposals/{id}/apply
- POST /api/actions/{id}/execute
- POST /api/actions/docker/{id}/execute
- POST /api/actions/restart-container

## Example tasks

- Check all my projects and tell me which ones look unhealthy.
- Investigate why torrent-studio is failing.
- Fix the crash in FinanceSMSTracker and prepare a patch.
- Check Docker containers and find anything using too much memory.

The agent investigates first, presents evidence, and requires approval before mutations. For coding tasks, it creates a detached worktree, edits and tests there, retries failed checks for up to three edit/verify cycles, then produces a diff for approval. Applying the diff requires approval and reruns verification; a failed post-apply check triggers a reverse-patch rollback attempt. This does not commit or push. Docker start/restart/stop, Git commits, durable memory writes, and exact source patches are approval-gated.

## Continuous VPS monitoring (optional)

The monitoring worker checks Docker container status/health, resource thresholds, bounded recent error-log excerpts, HTTP health checks, incident deduplication, and email alerts on incident/recovery transitions. See [monitoring/README.md](monitoring/README.md). Keep SMTP credentials in a private .env.monitor; never commit secrets. The monitor uses a private Docker socket proxy configured for GET-only API requests and does not perform restarts or deployments.
