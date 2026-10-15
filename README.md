# Oracle VPS Agent

A self-hosted multi-agent engineering control plane for managing software projects and services on an Oracle VPS.

## Agent team

- **Architect** — plans work before execution and reviews the worker's report afterward.
- **Worker/orchestrator** — uses repository and VPS tools to investigate and produce exact patch proposals.
- **Specialists** — project discovery, coding, DevOps, Git, debugging, security, verification and memory.
- **Verification** — runs bounded project-aware syntax, test and build checks.

The architect and worker can use different model IDs behind any compatible OpenAI Chat Completions gateway. For coding tasks, the worker can create a detached Git worktree, edit files only inside that worktree, run bounded project-aware checks, repair failures, and submit a diff for approval. Applying the verified diff to the original checkout requires approval; committing and pushing remain separate approval-gated actions. The gateway supplies model access; repository tools, shell execution, tests and approval handling remain on the VPS.

## Model configuration

Legacy deployments continue to work with `OPENROUTER_API_KEY` and `OPENROUTER_MODEL`. Configure these optional variables in the private VPS `.env`:

```env
AI_BASE_URL=https://openrouter.ai/api/v1/chat/completions
AI_API_KEY=
OPENROUTER_API_KEY=...
ARCHITECT_MODEL=your-strong-planning-model
WORKER_MODEL=your-cheaper-tool-capable-model
AI_REQUEST_TIMEOUT=120
```

For FreeLLMAPI or another OpenAI-compatible gateway, set `AI_BASE_URL` to its **chat-completions endpoint** and `AI_API_KEY` to its access key. If `AI_API_KEY` is empty, `OPENROUTER_API_KEY` is used for backwards compatibility. Model IDs must be exposed by the configured gateway. The worker model must support tool/function calling.

Each task gets an architect planning call, a worker tool loop, and an architect review call. If planning fails, the worker can still proceed and the error is reported. If review fails, the result is explicitly marked as not independently reviewed. Using the same model for both roles is compatible but does not provide true model diversity.

## Safety model

Read operations are available automatically. State-changing operations require an approval record. Source patches record exact old_text, new_text, target paths and SHA-256 snapshots. Applying a patch requires the snapshot to still match and creates a backup first.

Container restarts also require approval. The generic shell is allowlisted and read-only. Docker and Git use dedicated tools. Sensitive files are blocked or redacted. Verification commands are bounded and project-aware.

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

## Continuous VPS monitoring (optional)

The monitoring worker checks Docker container status/health, resource thresholds, bounded recent error-log excerpts, HTTP health checks, incident deduplication, and email alerts on incident/recovery transitions.

See [monitoring/README.md](monitoring/README.md). Keep SMTP credentials in a private `.env.monitor`; never commit secrets. The monitor uses a private Docker socket proxy configured for GET-only API requests and does not perform restarts or deployments. The private agent API provides authenticated read-only diagnostics for allowlisted containers.
