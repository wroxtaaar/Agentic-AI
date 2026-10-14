# Private VPS diagnostics MCP

This MCP server exposes bounded read-only tools for the VPS diagnostics allowlist. It is intended to be connected to ChatGPT using OpenAI Secure MCP Tunnel. The MCP service is not published on a host port and does not mount the Docker socket.

## Tools exposed

- `list_containers`: summary status, health, restart counts.
- `get_container_details(name)`: status, image, CPU/memory, restart count for an allowlisted container.
- `get_container_logs(name, lines=100)`: recent redacted logs, bounded to 200 lines.
- `search_container_logs(name, terms, lines=200)`: searches the recent bounded log tail for comma-separated literal, case-insensitive terms. Default terms target cache, OTT, Favourites/Classics, poster, provider, rate-limit, and error events. This filters returned logs locally and does not execute a shell command.

The agent API is configured with `DIAGNOSTICS_MAX_LOG_LINES=200`; its hard maximum remains 200 lines and log output remains bounded/redacted. The MCP bridge independently enforces the container allowlist and term count/length limits.

Container names are restricted to `home`, `docker-control-bot`, `agentic-ai`, and `agentic-monitor`. The MCP service receives only the `AGENT_API_TOKEN` environment variable and does not receive the Docker socket or host filesystem mounts. It calls only fixed GET diagnostics routes on the agent API.

## Deployment verification

The push to `main` should trigger the existing deployment workflow. After it completes, verify on the VPS:

```bash
cd ~/Agentic-AI
docker compose ps diagnostics-mcp agent
docker compose logs --tail=80 diagnostics-mcp
docker compose config --services
```

Confirm that the MCP service is running and that Compose does not publish port 8788 on the host. The token is read from the existing `AGENT_API_TOKEN` in `~/Agentic-AI/.env`; do not paste it into chat.

## Connect to ChatGPT privately

1. In OpenAI Platform, open the **Tunnels** settings for the personal Platform organization associated with your ChatGPT account. Create a tunnel and note its `tunnel_id`.
2. Create a restricted runtime API key with **Tunnels Read + Use** permissions, following the Secure MCP Tunnel guide. Do not paste the key into ChatGPT or a conversation.
3. On the VPS, install the latest `tunnel-client` release from the official `openai/tunnel-client` project. Run `tunnel-client help quickstart` and follow the supported Linux setup. Keep the runtime key in a private environment or the client's supported secret input, never in the Git repository or shell command history.
4. Configure the client to forward to the private MCP endpoint at `http://127.0.0.1:8788/mcp` (or the Compose service address if the tunnel client runs in the same Docker network). Run `tunnel-client doctor --profile <profile> --explain`, then `tunnel-client run --profile <profile>`; keep it running.
5. In ChatGPT web, open settings for apps/connectors and choose the custom MCP server/tunnel option if available for your account. Select or paste the tunnel ID, then inspect the discovered tools. Enable the connection only if the tools shown are the four read-only diagnostics tools described above.
6. Test by asking ChatGPT to list the VPS containers, then use `search_container_logs` for `home` with terms such as `cache,ott,favourites,poster,watchmode,tmdb,429,error,warn`.

Secure MCP Tunnel is outbound-only from the VPS; this design does not require a public listener or firewall port. Tunnel access and ChatGPT custom MCP access are separately permissioned. Availability depends on the ChatGPT plan/workspace's custom MCP support and Platform organization permissions. Current OpenAI guidance: https://developers.openai.com/api/docs/guides/secure-mcp-tunnels and https://help.openai.com/en/articles/12584461-developer-mode-and-full-mcp-connectors-in-chatgpt.

## Security boundaries

- No tools for shell commands, file reads, container restarts, deployments, or arbitrary HTTP URLs.
- No public host port for the MCP server.
- No Docker socket or host filesystem mounted into the MCP service.
- Only fixed GET requests to the authenticated diagnostics API.
- The existing agent API still has other control-plane routes; this MCP bridge does not expose those routes as tools.
- Log redaction is best-effort. Treat log output as sensitive and do not share secrets in prompts.
