# Continuous VPS monitoring

The monitor is a separate worker. It does not restart, start, stop, or deploy containers. It checks a configured list of containers, their Docker health/status, container CPU/memory percentages, recent error-looking log lines, and configured HTTP health URLs. It deduplicates incidents in a persistent SQLite database and sends email on first detection and recovery.

## Security design

- The monitor uses a dedicated Docker socket proxy on a private Compose network.
- The proxy allows only Docker API GET requests (POST=0) and is not published to the host.
- The monitor receives only the proxy endpoint, not the raw Docker socket.
- SMTP credentials live in .env.monitor, which is ignored by Git and is only passed to the monitor service.
- Email bodies are bounded and apply best-effort redaction. Logs can still contain personal or application data; review the recipients and do not forward raw reports publicly.
- Monitoring is read-only. A diagnosis never triggers an automatic restart, source edit, or deployment.

This checks container CPU and memory, not total host memory or root-filesystem free space. Docker container log matching is heuristic; an ERROR line may not always mean an outage. Tune thresholds and log patterns for the application.

## Configure on the VPS

Before deploying this branch, from ~/Agentic-AI:

```bash
cp .env.monitor.example .env.monitor
chmod 600 .env.monitor
nano .env.monitor
```

Set the SMTP host, port, username, password/app password, and recipient. Use STARTTLS with SMTP_PORT=587 and SMTP_USE_SSL=false, or implicit TLS with SMTP_PORT=465 and SMTP_USE_SSL=true. The sender defaults to the SMTP username if ALERT_EMAIL_FROM is blank.

Keep the actual .env.monitor file off GitHub and never paste its contents into chat.

In the normal .env, tune if desired:

- MONITOR_INTERVAL_SECONDS=300 — five-minute polling; minimum is 60 seconds.
- MONITOR_CONTAINERS=home,docker-control-bot,agentic-ai — Docker container names to inspect.
- MONITOR_HEALTH_URLS=http://host.docker.internal:10000/health — comma-separated HTTP health endpoints.
- MONITOR_CPU_ALERT_PERCENT=95 and MONITOR_MEMORY_ALERT_PERCENT=90 — per-container thresholds.
- MONITOR_LOG_SINCE=10m and MONITOR_LOG_TAIL=120 — bounded log window and tail size.
- MONITOR_RECOVERY_MISSES=2 — number of consecutive checks without an issue before recovery is reported.

## Test after deployment

```bash
cd ~/Agentic-AI
docker compose config --quiet
docker compose up -d --build
docker compose ps
docker compose logs --tail=100 monitor
docker compose logs --tail=100 docker-socket-proxy
```

Expected: agentic-monitor stays running and prints periodic check summaries. If SMTP is not configured, it logs a configuration warning and retries email delivery on subsequent checks.

To test email delivery safely, use a temporary, intentionally invalid health URL in MONITOR_HEALTH_URLS, deploy/recreate the monitor, confirm an alert arrives, then restore the real URL. Do not stop production containers merely to test notifications.

## ChatGPT diagnosis integration: next phase

This branch adds monitoring and email only. It does not expose a new public API or automatically forward logs to ChatGPT. The follow-up integration should be a narrowly scoped, authenticated read-only endpoint (or MCP server) that returns bounded, redacted incident summaries and selected log excerpts. Keep the existing full-control agent API private; never expose the Docker socket proxy or the control API to the public internet.
