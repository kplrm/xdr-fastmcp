# Contributing to xdr-fastmcp

This repository owns the Python MCP server, tool discovery, and its container/deployment configuration. Start with the [README](README.md) for local deployment, credentials, and client setup.

## Development and validation

Use Docker Engine with Docker Compose. The Dockerfile owns the Python version, and `requirements.txt` owns the pinned server dependencies. For tool checks, provide test OpenSearch credentials through the local environment as described in the README.

```bash
docker compose -f docker-compose.xdr-fastmcp.yml up -d --build
docker compose -f docker-compose.xdr-fastmcp.yml ps
curl --fail http://127.0.0.1:8000/health
```

Connect a test MCP client to `http://127.0.0.1:8000/mcp`, list tools, and call each changed tool with representative and invalid inputs. Check its argument schema, returned data, and failure behavior; `/health` alone does not exercise tool calls. Stop the local deployment with:

```bash
docker compose -f docker-compose.xdr-fastmcp.yml down
```

There is currently no automated test suite. Add focused regression coverage for new server/tool behavior and document the manual checks in your PR.

## Engineering expectations

- Put tool functions in `tools/` with unique public names, Python type hints, and clear docstrings. Public functions defined in those modules are automatically exposed.
- Cover tool discovery, duplicate names, import failures, input validation, and output compatibility when relevant.
- Keep credentials in environment variables or deployment Secrets; preserve TLS verification and prevent credentials from leaking through logs or redirects.
- Keep existing telemetry tools read-only unless a different capability is explicitly agreed upon.
- Update `requirements.txt` and rebuild the image for dependency changes; runtime tool files have a separate deployment lifecycle.
- Preserve dependency/tool licenses and notices. Runtime mounting or downloading does not itself exempt combined tools from applicable AGPL obligations.

## Issues and pull requests

Use this repository's [issue tracker](https://github.com/kplrm/xdr-fastmcp/issues) for general questions, reproducible bugs, and proposals. Discuss substantial changes before implementation.

1. Fork the repository and branch from `main`.
2. Keep the change focused and follow the existing code style.
3. Add regression coverage for changed behavior and update affected documentation.
4. In your PR, explain the problem, resulting behavior, validation performed, and compatibility impact. List any checks you could not run, including the reason.

Use sanitized logs and fixtures; remove secrets and identifying customer data before posting.

## License and attribution

By submitting a contribution, you agree to license your original changes under the [GNU Affero General Public License, version 3 only](LICENSE) (`AGPL-3.0`). You retain copyright in your contributions. Submit only work you have the right to contribute, and preserve existing copyright and third-party license notices.

## Security reports

Report vulnerabilities through this repository's [private vulnerability reporting](https://github.com/kplrm/xdr-fastmcp/security/advisories/new) when enabled. Include affected versions, reproduction steps, impact, and sanitized supporting details. Keep vulnerability, bypass, and credential details out of public issues.

If private reporting is unavailable, open an issue asking the maintainer for a private reporting channel without describing the vulnerability.

## Conduct

Be respectful, direct, and technically concrete in issues, reviews, and discussions.
