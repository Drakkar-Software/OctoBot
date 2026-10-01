#  Demo-only HTTP helpers for agent seed bootstrap.

import base64
import json
import typing
import urllib.error
import urllib.request


def basic_auth_header(wallet_address: str, passphrase: str) -> dict[str, str]:
    token = base64.b64encode(f"{wallet_address}:{passphrase}".encode()).decode()
    return {"Authorization": f"Basic {token}"}


def request_json(
    method: str,
    url: str,
    headers: dict[str, str],
    payload: typing.Optional[dict] = None,
) -> tuple[int, typing.Any]:
    body = None
    request_headers = dict(headers)
    if payload is not None:
        body = json.dumps(payload).encode("utf-8")
        request_headers["Content-Type"] = "application/json"
    request = urllib.request.Request(url, data=body, headers=request_headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            raw = response.read()
            if not raw:
                return response.status, None
            return response.status, json.loads(raw.decode("utf-8"))
    except urllib.error.HTTPError as error:
        raw = error.read()
        parsed = json.loads(raw.decode("utf-8")) if raw else None
        return error.code, parsed
