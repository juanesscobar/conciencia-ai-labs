"""Signals adapter verified against core 383ac44; transport is injected."""
import json
from urllib.parse import urlparse
from urllib.request import Request, build_opener, HTTPRedirectHandler, ProxyHandler
from uuid import UUID

from .domain import canonical


class AdapterError(RuntimeError):
    pass


def signal_payload(mission_id: str, run: dict, kind: str = "risk") -> dict:
    UUID(mission_id)
    if kind not in {"risk", "finding", "decision"}:
        raise ValueError("SIMULATED unsupported signal type")
    return {"mission_id": mission_id, "type": kind,
            "title": f"SIMULATED {run['scenario_id']} {run['diagnosis']}",
            "summary": f"SIMULATED; run={run['run_id']}; mode={run['integration_mode']}",
            "source_step": f"ai-factory-lab:{run['scenario_id']}",
            "evidences": [{"kind": "data", "content": canonical(run),
                           "source": f"lab_sim://{run['scenario_id']}/{run['run_id']}"}]}


class SignalsAdapter:
    def __init__(self, transport):
        self.transport = transport

    def emit(self, payload: dict) -> dict:
        try:
            status, body = self.transport("POST", "/api/v1/signals/", payload)
        except Exception as error:
            # Never print transport errors which may contain tokens/request bodies.
            raise AdapterError("SIMULATED signal delivery outcome UNKNOWN; no automatic retry") from None
        if status != 201:
            raise AdapterError(f"SIMULATED core rejected signal (HTTP {status}); not delivered")
        try:
            UUID(body["id"])
            UUID(body["mission_id"])
            if (body["mission_id"] != payload["mission_id"] or body["type"] != payload["type"]
                    or body["title"] != payload["title"] or body["status"] != "new"
                    or not isinstance(body["evidence"], list) or not body["evidence"]):
                raise ValueError()
        except (KeyError, TypeError, ValueError, AttributeError):
            raise AdapterError("SIMULATED invalid core acknowledgement; outcome UNKNOWN") from None
        return {"environment": "SIMULATED", "delivery": "acknowledged", "signal_id": body["id"]}


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class LocalHTTPTransport:
    """Opt-in loopback transport. Not invoked by the offline CLI or test demo."""
    def __init__(self, base_url: str, token: str):
        url = urlparse(base_url)
        if (url.scheme != "http" or url.hostname not in {"127.0.0.1", "localhost", "::1"}
                or url.username or url.password or url.path not in {"", "/"} or url.query or url.fragment):
            raise ValueError("SIMULATED adapter accepts only an explicit loopback HTTP origin")
        self.base_url = base_url.rstrip("/")
        self.token = token

    def __call__(self, method, path, payload):
        from urllib.error import HTTPError
        if method != "POST" or path != "/api/v1/signals/":
            raise ValueError("SIMULATED unsupported endpoint")
        request = Request(self.base_url + path, canonical(payload).encode(), method=method,
                          headers={"Content-Type": "application/json", "Authorization": "Bearer " + self.token})
        try:
            with build_opener(ProxyHandler({}), NoRedirect()).open(request, timeout=5) as response:
                return response.status, json.loads(response.read(2_000_000))
        except HTTPError as error:
            return error.code, {}
