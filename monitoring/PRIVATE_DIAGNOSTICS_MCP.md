# Private VPS diagnostics MCP

This adds a separate MCP server exposing only three read-only tools for the VPS diagnostics allowlist. It is intended to be connected to ChatGPT using OpenAI Secure MCP Tunnel. The MCP service is not published on a host port and does not mount the Docker socket.

## Tools exposed

- `list_containers`: summary status, health, restart counts.
- `get_container_details(name)`: status, image, CPU/memory, restart count for an allowlisted container.
- `get_container_logs(name, lines=80)`: recent redacted logs, bounded to 200 lines by the MCP bridge and by the diagnostics API's own limits.

Container names are restricted to `home`, `docker-control-bot`, `agentic-ai`, and `agentic-monitor`. The MCP service has only the `AGENT_API_TOKEN` environment variable from the agent's .env; it does not receive other app secrets, the Docker socket, or host mounts. It calls only fixed GET diagnostics routes on the agent API.

## Deploy

The repository deploy workflow will validate and deploy the new `diagnostics-mcp` Compose service after this change is merged to `main`. It uses the existing `AGENT_API_TOKEN` value from `~/Agentic-AI/.env`. No additional secret needs to be pasted into chat.

After deployment, verify on the VPS:

```bash
cd ~/Agentic-AI
docker compose ps diagnostics-mcp
docker compose logs --tail=80 diagnostics-mcp
docker compose exec diagnostics-mcp python -c "import urllib.request; print(urllib.request.urlopen('http://127.0.0.1:8788/mcp', timeout=5).status)"
```

The last command may return a protocol-specific HTTP status because `/mcp` is a Streamable HTTP endpoint, not a normal browser page; container health and logs are the primary initial checks. Port 8788 must remain unpublished in Compose.

## Connect to ChatGPT privately

1. In OpenAI Platform, open the **Tunnels** settings for the personal Platform organization associated with your ChatGPT account. Create a tunnel and note its `tunnel_id`.
2. Create a restricted runtime API key with **Tunnels Read + Use** permissions, following the Secure MCP Tunnel guide. Do not paste the key into ChatGPT or a conversation.
3. On the VPS, install the latest `tunnel-client` release from the official `openai/tunnel-client` project. Run `tunnel-client help quickstart` and follow the supported Linux setup. Keep the runtime key in a private environment or the client's supported secret input, never in the Git repository or shell command history.
4. Configure the client to forward to the private MCP endpoint at `http://127.0.0.1:8788/mcp` (or the Compose service address if the tunnel client runs in the same Docker network). Run `tunnel-client doctor --profile <profile> --explain`, then `tunnel-client run --profile <profile>`; keep it running.
5. In ChatGPT web, open **Settings / Plugins** (the exact label may vary), choose **Add custom MCP server**, select **Tunnel**, and select/paste the same tunnel ID. Create the app and inspect the discovered tools. Only enable this app if the tools shown are the three read-only diagnostics tools described above.
6. Test by asking ChatGPT to list the VPS containers, then request recent logs for `agentic-ai`.

Secure MCP Tunnel is outbound-only from the VPS; this design does not require a public listener or firewall port. Tunnel access and ChatGPT custom MCP access are separately permissioned. Availability depends on the ChatGPT plan/workspace's custom MCP support and the Platform organization permissions. Current OpenAI guidance: https://developers.openai.com/api/docs/guides/secure-mcp-tunnels and https://help.openai.com/en/articles/12584461-developer-mode-and-full-mcp-connectors-in-chatgpt.

## Security boundaries

- No tools for shell commands, file reads, container restarts, deployments, or arbitrary HTTP URLs.
- No public host port for the MCP server.
- No Docker socket or host filesystem mounted into the MCP service.
- Only fixed GET requests to the authenticated diagnostics API.
- The existing agent API still has other control-plane routes; this MCP bridge does not expose those routes as tools.
- Log redaction is best-effort. Treat log output as sensitive and do not share secrets in prompts.
