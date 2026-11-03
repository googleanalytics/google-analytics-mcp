# Troubleshooting

## macOS gRPC DNS resolution errors

If Analytics API calls fail with a DNS resolution error such as
`Failed to resolve analyticsadmin.googleapis.com`, while the hostname resolves
normally from your terminal, try configuring gRPC to use the system DNS
resolver.

On macOS, grpcio's default c-ares resolver can fail to resolve hostnames when
using VPNs or split DNS. This can affect any MCP client, including Gemini CLI
and Claude Code.

### Gemini CLI

Add `"GRPC_DNS_RESOLVER": "native"` to the server's `env` object in
`~/.gemini/settings.json`:

```json
{
  "mcpServers": {
    "analytics-mcp": {
      "command": "pipx",
      "args": ["run", "analytics-mcp"],
      "env": {
        "GOOGLE_APPLICATION_CREDENTIALS": "PATH_TO_CREDENTIALS_JSON",
        "GOOGLE_CLOUD_PROJECT": "YOUR_PROJECT_ID",
        "GRPC_DNS_RESOLVER": "native"
      }
    }
  }
}
```

### Claude Code

Add `-e "GRPC_DNS_RESOLVER=native"` to the `claude mcp add` command:

```shell
claude mcp add analytics-mcp \
  --scope user \
  -e "GOOGLE_APPLICATION_CREDENTIALS=PATH_TO_CREDENTIALS_JSON" \
  -e "GOOGLE_CLOUD_PROJECT=YOUR_PROJECT_ID" \
  -e "GRPC_DNS_RESOLVER=native" \
  -- pipx run analytics-mcp
```

This is an optional workaround. Leave it unset unless you encounter this
specific DNS resolution issue. It selects gRPC's native `getaddrinfo()`
resolver instead of c-ares when c-ares is the configured default.
