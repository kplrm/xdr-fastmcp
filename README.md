# XDR FastMCP

A Dockerized [FastMCP](https://gofastmcp.com/) server that automatically exposes
Python functions from `tools/` over Streamable HTTP.

<div align="center">
  <img src="images/XDR_FastMCP-example.png" alt="XDR FastMCP tool example" width="400">
</div>

## Deploy locally

Install Docker Engine on Linux with Docker Compose, then run from this repository:

```sh
docker compose -f docker-compose.xdr-fastmcp.yml up -d --build
docker compose -f docker-compose.xdr-fastmcp.yml ps
curl --fail http://127.0.0.1:8000/health
```

Connect an MCP client using Streamable HTTP at `http://127.0.0.1:8000/mcp`.
`/health` reports server availability and the number of loaded tools.

```sh
# Inspect logs / stop and remove the local deployment
docker compose -f docker-compose.xdr-fastmcp.yml logs -f
docker compose -f docker-compose.xdr-fastmcp.yml down
```

Compose mounts local `tools/` at `/app/tools` read-only and runs as a non-root
user. Host networking reaches local OpenSearch; MCP listens on all interfaces.
There is no MCP authentication configured; add authentication and TLS before
exposing it beyond your local machine.

For a standalone image build: `docker build -t xdr-fastmcp:local .`.

## Container image

[GitHub Actions](.github/workflows/container.yml) publishes Linux amd64 images
to `ghcr.io/kplrm/xdr-fastmcp` on pushes to `main` or manual runs. Main builds
update `latest`; every build also has a `sha-<full-commit>` tag.
Publishing uses `GITHUB_TOKEN`; no additional repository secret is needed.

After the first run, [set the package visibility to public](https://docs.github.com/en/packages/learn-github-packages/configuring-a-packages-access-control-and-visibility)
for pulls without credentials, including the Kubernetes deployment below.

```sh
docker pull ghcr.io/kplrm/xdr-fastmcp:latest
```

## Deploy on Kubernetes (one pod)

Run from this repository on a host with cluster access. This assumes namespace `opensearch`.

### Create the OpenSearch user and role

Use the `fastmcp` user with only the `telemetry_read` role, scoped by
[telemetry-read-role.json](deploy/telemetry-read-role.json) to read `xdr-agent-telemetry`.

```bash
OS_URL='https://OPENSEARCH_HOST:PORT'
OS_CA='/path/to/opensearch-ca.pem'
curl --fail-with-body --cacert "$OS_CA" --user admin \
  --request PUT "$OS_URL/_plugins/_security/api/roles/xdr_fastmcp" \
  --header 'Content-Type: application/json' \
  --data-binary @deploy/xdr-fastmcp-role.json
```

```bash
read -rsp 'FastMCP password (same as private .env): ' FASTMCP_PASSWORD
printf '\n'
jq -n --arg password "$FASTMCP_PASSWORD" \
  '{password: $password, opendistro_security_roles: ["telemetry_read"]}' |
curl --fail-with-body --cacert "$OS_CA" --user admin \
  --request PUT "$OS_URL/_plugins/_security/api/internalusers/fastmcp" \
  --header 'Content-Type: application/json' --data-binary @-
unset FASTMCP_PASSWORD
```

## OpenSearch configuration

Edit local `.env` (copy of `.env.example`). With `OPENSEARCH_VERIFY_TLS=true`,
copy the CA from the running OpenSearch and set `OPENSEARCH_CA_FILE` accordingly:

```sh
docker cp opensearch-node:/usr/share/opensearch/config/root-ca.pem certs/opensearch-root-ca.pem
```

## Tool discovery

Store Python tools in local `tools/`; they are excluded from the image.
Compose mounts this folder directly. In Kubernetes, the init container
downloads the files from GitHub into the pod's shared volume.
The server registers public functions from these files at startup.
For Kubernetes, push tool changes to GitHub and restart the deployment.
For Compose, restart after editing tools:

```sh
docker compose -f docker-compose.xdr-fastmcp.yml restart xdr-fastmcp
```

Add Python dependencies to `requirements.txt`, then rebuild the image and update
the container:

```sh
docker compose -f docker-compose.xdr-fastmcp.yml up -d --build
```

## License

XDR FastMCP is free software under [GNU AGPLv3](LICENSE), which requires sharing source code when distributed or when modified versions serve remote users.

- **Usage:** use, modify, redistribute, and sell it, including cloud hosting, while following the license.
- **Distribution:** share the complete source code with recipients, including your changes and build files, using a method permitted by AGPLv3.
- **Network use (§13):** if you run a modified version, prominently offer every remote user free access to its complete source code, even without distribution.
- **Copyleft:** keep covered modified versions under AGPLv3, preserve notices, and identify your changes. Dependencies retain their own licenses.
- **Warranty:** provided without warranty; liability is limited as specified in the license.

> Sharing source code with the required users is mandatory.

- **Custom tools:** adding tools can create an AGPL-covered combined program. When distributing that program or serving a modified version remotely, include the tools’ source in the required source offer. Independent works, or tools used only locally without distribution, may remain private. Excluding tools from the image build does not create an exemption.
