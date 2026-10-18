# Read-only diagnostics API

The existing FastAPI control plane now exposes three read-only diagnostics endpoints. They use the existing `AGENT_API_TOKEN` Bearer authentication and the service should remain bound to `127.0.0.1:8787` or a private Tailscale interface. Do not publish this API to the public internet.

## Endpoints

- `GET /api/diagnostics/containers` — status, health, and restart count for the configured allowlist.
- `GET /api/diagnostics/containers/{name}` — image, state, health, start time, restart count, and a snapshot of container CPU/memory.
- `GET /api/diagnostics/containers/{name}/logs?lines=100` — recent timestamped logs, redacted and capped at 200 lines / 12,000 characters.

Default allowlist: `home,docker-control-bot,agentic-ai,agentic-monitor`. Override with `DIAGNOSTICS_CONTAINERS` in the agent's private `.env`. Log cap can be lowered with `DIAGNOSTICS_MAX_LOG_LINES` (effective range 20–200).

Requests must include `Authorization: Bearer $AGENT_API_TOKEN`. Names outside the configured allowlist return 404. There are no endpoints for shell execution, arbitrary container selection, restarting, deploying, reading arbitrary files, or changing service state. These routes are still part of the existing control API, so authentication and private network isolation are mandatory.

## Use from a trusted workstation

Create an SSH tunnel (replace the host alias if yours differs):

```bash
ssh -N -L 8787:127.0.0.1:8787 oracle-torrent
```

In a second terminal, set the token locally without putting it in command history:

```bash
read -rsp 'Agent API token: ' AGENT_API_TOKEN; echo
export AGENT_API_TOKEN
curl -fsS -H "Authorization: Bearer $AGENT_API_TOKEN" http://127.0.0.1:8787/api/diagnostics/containers
curl -fsS -H "Authorization: Bearer $AGENT_API_TOKEN" http://127.0.0.1:8787/api/diagnostics/containers/home
curl -fsS -H "Authorization: Bearer $AGENT_API_TOKEN" 'http://127.0.0.1:8787/api/diagnostics/containers/home/logs?lines=80'
unset AGENT_API_TOKEN
```

You can paste the JSON response into ChatGPT for diagnosis. Do not paste the token or raw `.env` files. Although redaction is applied, it is best-effort and cannot guarantee every application-specific secret is recognized.

## Important limitation

This adds a secured read-only HTTP interface, but it does **not** create a native ChatGPT connector or grant this conversation a direct network path to your VPS. Direct on-demand retrieval from ChatGPT would require a separately hosted, authenticated connector/MCP service reachable through a private or explicitly secured integration. Do not expose the full-control API publicly to achieve that.
