"""Read network telemetry using credentials supplied through the environment."""

import base64
import json
import os
import ssl
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, HTTPSHandler, Request, build_opener


class _NoRedirects(HTTPRedirectHandler):
    """Keep authorization headers from being forwarded to another endpoint."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def top_destination_ips() -> dict:
    """Return the top five destination IPs by event count across all network telemetry.

    Counts both opened and closed events, not unique connections. Events without
    a destination IP do not enter the ranking. Reads all available dates; counts
    can change if telemetry is updated during pagination.
    """
    url = os.environ.get("OPENSEARCH_URL", "").rstrip("/")
    parsed = urlsplit(url)
    if (parsed.scheme not in {"http", "https"} or not parsed.netloc
            or parsed.username or parsed.password or parsed.query or parsed.fragment):
        raise ValueError("Set OPENSEARCH_URL to an HTTP(S) endpoint without credentials or query parameters.")

    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    token = os.environ.get("TOKEN", "").strip()
    username = os.environ.get("OPENSEARCH_USERNAME", "")
    password = os.environ.get("OPENSEARCH_PASSWORD", "")
    if token:
        if "\r" in token or "\n" in token:
            raise ValueError("TOKEN must be a single-line value.")
        # OpenSearch API keys use the os_ prefix; other tokens use Bearer.
        scheme = "ApiKey" if token.startswith("os_") else "Bearer"
        headers["Authorization"] = f"{scheme} {token}"
    elif username:
        credentials = base64.b64encode(f"{username}:{password}".encode()).decode()
        headers["Authorization"] = f"Basic {credentials}"
    elif password:
        raise ValueError("Set OPENSEARCH_USERNAME when using OPENSEARCH_PASSWORD.")

    verify = os.environ.get("OPENSEARCH_VERIFY_TLS", "true").lower()
    if verify not in {"true", "false"}:
        raise ValueError("OPENSEARCH_VERIFY_TLS must be true or false.")
    # Trust the local OpenSearch CA without disabling certificate verification.
    ca_file = os.environ.get("OPENSEARCH_CA_FILE") or None
    context = ssl.create_default_context(cafile=ca_file) if verify == "true" else ssl._create_unverified_context()
    opener = build_opener(_NoRedirects(), HTTPSHandler(context=context))
    endpoint = (f"{url}/.xdr-agent-telemetry-*/_search"
                "?expand_wildcards=open,hidden&allow_no_indices=true&ignore_unavailable=true")
    composite = {"size": 1000, "sources": [
        {"ip": {"terms": {"field": "payload.destination.ip"}}},
    ]}
    body = {
        "size": 0, "track_total_hits": True,
        "query": {"term": {"event.module": "telemetry.network"}},
        "aggs": {"destinations": {"composite": composite}},
    }
    top = []
    total = 0
    while True:
        request = Request(endpoint, data=json.dumps(body).encode(), headers=headers, method="POST")
        try:
            with opener.open(request, timeout=30) as response:
                result = json.load(response)
        except HTTPError as error:
            # Never expose response bodies, credentials or headers to MCP clients.
            raise RuntimeError(f"OpenSearch query failed (HTTP {error.code}). Check authentication and index permissions.") from None
        except (URLError, TimeoutError) as error:
            reason = error.reason if isinstance(error, URLError) else error
            if isinstance(reason, ssl.SSLCertVerificationError):
                raise RuntimeError("OpenSearch TLS verification failed. Check OPENSEARCH_CA_FILE and the certificate hostname.") from None
            if isinstance(reason, ConnectionRefusedError):
                raise RuntimeError("OpenSearch connection refused. Check the host, HTTPS port (usually 9200) and container networking.") from None
            if isinstance(reason, TimeoutError):
                raise RuntimeError("OpenSearch request timed out. Check connectivity and cluster load.") from None
            raise RuntimeError("Cannot reach OpenSearch. Check OPENSEARCH_URL, connectivity and TLS settings.") from None
        if result.get("timed_out") or result.get("_shards", {}).get("failed", 0):
            raise RuntimeError("OpenSearch returned incomplete results; retry the query.")
        if body["track_total_hits"]:
            total = int(result["hits"]["total"]["value"])
            body["track_total_hits"] = False
        aggregation = result["aggregations"]["destinations"]
        # Page every IP to avoid approximate top counts across multiple shards.
        for bucket in aggregation["buckets"]:
            top.append({"ip": str(bucket["key"]["ip"]), "count": int(bucket["doc_count"])})
        top = sorted(top, key=lambda item: (-item["count"], item["ip"]))[:5]
        after = aggregation.get("after_key")
        if not aggregation["buckets"] or after is None:
            break
        if after == composite.get("after"):
            raise RuntimeError("OpenSearch pagination did not advance.")
        composite["after"] = after
    return {"total_network_events": total, "destinations": top}
