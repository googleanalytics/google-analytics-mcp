# Podman and Streamable HTTP interoperability

This deployment keeps Python, the MCP runtime, and all dependencies inside a
rootless Podman container in Ubuntu on WSL. MCP clients connect to one local,
vendor-neutral Streamable HTTP endpoint:

```text
http://127.0.0.1:8081/mcp
```

The host port is bound only to loopback. The server has no MCP-layer
authentication, so do not publish it on `0.0.0.0` or expose it to a LAN.

## 1. Create credentials in Google Cloud Console

1. Open [Google Cloud Console](https://console.cloud.google.com/) and select or
   create the project that will own the service account.
2. Open **APIs & Services > Library** and enable:
   - **Google Analytics Data API**
   - **Google Analytics Admin API**
3. Open **IAM & Admin > Service Accounts** and choose **Create service
   account**.
4. Give it a descriptive name such as `google-analytics-mcp`. Do not grant a
   Google Cloud project role: access to Analytics data is granted separately
   in GA4.
5. Open the new service account, select **Keys > Add key > Create new key**,
   choose **JSON**, and download the file.
6. Keep the JSON outside this repository. Never commit it, copy it into the
   image, paste it into an MCP client configuration, or share its contents.
7. In Google Analytics, open **Admin > Property access management** for the
   required GA4 property, add the service-account email, and grant **Viewer**.
   Use account-level access only when the server must see every property in the
   Analytics account.
8. If revenue or cost metrics are needed, make sure the GA4 role does not
   restrict access to those metrics.

If organization policy prevents service-account key creation, ask the Google
Cloud administrator for an approved workload-identity alternative. Do not
bypass the policy.

## 2. Build the image in Ubuntu on WSL

Run from the repository directory mounted in WSL:

```bash
podman build \
  --pull=missing \
  --tag localhost/google-analytics-mcp:local \
  --file Dockerfile \
  .
```

No Python package or build tool is installed in Windows or WSL.

## 3. Start the hardened local container

Translate the Windows JSON path to its WSL form. For example,
`C:\Users\YOUR_WINDOWS_USER\.config\google-analytics\credentials.json` becomes
`/mnt/c/Users/YOUR_WINDOWS_USER/.config/google-analytics/credentials.json`.

```bash
podman run --detach \
  --name google-analytics-mcp \
  --replace \
  --restart unless-stopped \
  --read-only \
  --security-opt no-new-privileges \
  --cap-drop all \
  --tmpfs /tmp:rw,nosuid,nodev,noexec,size=64m \
  --publish 127.0.0.1:8081:8080 \
  --volume /ABSOLUTE/WSL/PATH/credentials.json:/run/secrets/google-analytics/credentials.json:ro \
  --env GOOGLE_APPLICATION_CREDENTIALS=/run/secrets/google-analytics/credentials.json \
  localhost/google-analytics-mcp:local
```

The container image selects stateful Streamable HTTP. Running
`analytics-mcp` outside that image still defaults to stdio for backward
compatibility.

For a persistent user service, copy
`deploy/podman/google-analytics-mcp.container.example` to
`~/.config/containers/systemd/google-analytics-mcp.container`, replace its
credential path, then reload and start the generated user service:

```bash
systemctl --user daemon-reload
systemctl --user enable --now google-analytics-mcp.service
```

The Quadlet file is configuration for Podman; it does not install software.

## 4. Configure MCP clients

Credentials remain solely in the server container. Every client receives only
the endpoint URL.

Codex `config.toml`:

```toml
[mcp_servers.google_analytics]
url = "http://127.0.0.1:8081/mcp"
```

Antigravity and Antigravity IDE MCP configuration:

```json
{
  "mcpServers": {
    "google_analytics": {
      "serverUrl": "http://127.0.0.1:8081/mcp"
    }
  }
}
```

Other MCP clients should select **Streamable HTTP** and use the same URL. Do
not configure SSE and do not append a session ID.

## 5. Verify

From any MCP client:

1. Confirm that `google_analytics` connects.
2. List tools and confirm that nine tools are available.
3. Call `get_property_details` with the authorized numeric property ID.
4. Start a second client at the same time and repeat the tool listing. Each
   client must maintain an independent MCP session.

To inspect service status without exposing credentials:

```bash
podman ps --filter name=google-analytics-mcp
podman logs --tail 100 google-analytics-mcp
```

Stop the manually started container with:

```bash
podman stop --time 15 google-analytics-mcp
```
