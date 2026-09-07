from __future__ import annotations

import json
import tempfile
import threading
import unittest
from http import HTTPStatus
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from lai_gateway.config import GatewayConfig
from lai_gateway.errors import ConfigError
from lai_gateway.server import GatewayHTTPServer
from lai_gateway.tokens import create_gateway_access_token, create_gateway_pairing_token

from .fake_harness import TOKEN, fake_harness, get_json


class RunningGateway:
    def __init__(self, config: GatewayConfig):
        self.server = GatewayHTTPServer(("127.0.0.1", 0), config)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)

    @property
    def url(self) -> str:
        host, port = self.server.server_address[:2]
        return f"http://{host}:{port}"

    def __enter__(self) -> "RunningGateway":
        self.thread.start()
        return self

    def __exit__(self, *exc: object) -> None:
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=5)


def post_json(url: str, payload: dict[str, object]) -> tuple[int, dict[str, object]]:
    request = Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urlopen(request, timeout=5) as response:
        body = json.loads(response.read().decode("utf-8"))
        return response.status, body


def post_empty_with_headers(url: str, headers: dict[str, str] | None = None) -> tuple[int, dict[str, object]]:
    request = Request(url, data=None, headers=headers or {}, method="POST")
    with urlopen(request, timeout=5) as response:
        return response.status, json.loads(response.read().decode("utf-8"))


def post_empty_error(url: str, headers: dict[str, str] | None = None) -> tuple[int, dict[str, object]]:
    request = Request(url, data=None, headers=headers or {}, method="POST")
    try:
        urlopen(request, timeout=5)
    except HTTPError as exc:
        return exc.code, json.loads(exc.read().decode("utf-8"))
    raise AssertionError("expected HTTPError")


def post_json_error(url: str, payload: dict[str, object]) -> tuple[int, dict[str, object]]:
    request = Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        urlopen(request, timeout=5)
    except HTTPError as exc:
        body = json.loads(exc.read().decode("utf-8"))
        return exc.code, body
    raise AssertionError("expected HTTPError")


def delete_with_headers(url: str, headers: dict[str, str] | None = None) -> tuple[int, dict[str, object]]:
    request = Request(url, headers=headers or {}, method="DELETE")
    with urlopen(request, timeout=5) as response:
        return response.status, json.loads(response.read().decode("utf-8"))


def delete_error(url: str, headers: dict[str, str] | None = None) -> tuple[int, dict[str, object]]:
    request = Request(url, headers=headers or {}, method="DELETE")
    try:
        urlopen(request, timeout=5)
    except HTTPError as exc:
        return exc.code, json.loads(exc.read().decode("utf-8"))
    raise AssertionError("expected HTTPError")


def get_json_with_headers(url: str, headers: dict[str, str] | None = None) -> tuple[int, dict[str, object]]:
    request = Request(url, headers=headers or {})
    with urlopen(request, timeout=5) as response:
        return response.status, json.loads(response.read().decode("utf-8"))


def get_json_error(url: str, headers: dict[str, str] | None = None) -> tuple[int, dict[str, object]]:
    request = Request(url, headers=headers or {})
    try:
        urlopen(request, timeout=5)
    except HTTPError as exc:
        return exc.code, json.loads(exc.read().decode("utf-8"))
    raise AssertionError("expected HTTPError")


class GatewayServerTest(unittest.TestCase):
    def _config(self, tmp: str, harness_url: str) -> GatewayConfig:
        token_file = Path(tmp) / "token"
        token_file.write_text(TOKEN, encoding="utf-8")
        return GatewayConfig(harness_url=harness_url, token_file=token_file)

    def test_gateway_exposes_read_only_harness_contract_status_and_readiness(self):
        with tempfile.TemporaryDirectory() as tmp, fake_harness() as harness:
            with RunningGateway(self._config(tmp, harness.url)) as gateway:
                self.assertEqual(get_json(f"{gateway.url}/healthz")["product"], "lai-gateway")
                contract = get_json(f"{gateway.url}/v1/harness/gateway-contract")
                self.assertEqual(contract["version"], "0.4.2")
                self.assertEqual(get_json(f"{gateway.url}/v1/harness/status")["ok"], True)
                readiness = get_json(f"{gateway.url}/v1/harness/readiness")
                self.assertEqual(readiness["overall"], "ready")

    def test_gateway_creates_sessions_without_exposing_runs(self):
        with tempfile.TemporaryDirectory() as tmp, fake_harness() as harness:
            with RunningGateway(self._config(tmp, harness.url)) as gateway:
                listed = get_json(f"{gateway.url}/v1/harness/sessions?limit=5")
                self.assertEqual(listed["sessions"][0]["session_id"], "s_test")

                request = Request(f"{gateway.url}/v1/harness/sessions", data=None, method="POST")
                with urlopen(request, timeout=5) as response:
                    body = json.loads(response.read().decode("utf-8"))
                    self.assertEqual(response.status, HTTPStatus.CREATED)
                self.assertEqual(body["session"]["session_id"], "s_test")
                self.assertEqual(
                    get_json(f"{gateway.url}/v1/harness/sessions/s_test")["session"]["session_id"],
                    "s_test",
                )

    def test_gateway_creates_only_read_only_runs(self):
        with tempfile.TemporaryDirectory() as tmp, fake_harness() as harness:
            with RunningGateway(self._config(tmp, harness.url)) as gateway:
                listed = get_json(f"{gateway.url}/v1/harness/runs?limit=5")
                self.assertEqual(listed["runs"][0]["control_run_id"], "cr_test")

                status, created = post_json(
                    f"{gateway.url}/v1/harness/runs",
                    {"mode": "plan", "task": "Summarize.", "session_id": "s_test"},
                )
                self.assertEqual(status, HTTPStatus.ACCEPTED)
                self.assertEqual(created["run"]["control_run_id"], "cr_test")
                fetched = get_json(f"{gateway.url}/v1/harness/runs/cr_test")
                self.assertEqual(fetched["run"]["status"], "succeeded")

    def test_gateway_blocks_write_modes_and_malformed_run_bodies(self):
        with tempfile.TemporaryDirectory() as tmp, fake_harness() as harness:
            with RunningGateway(self._config(tmp, harness.url)) as gateway:
                status, body = post_json_error(
                    f"{gateway.url}/v1/harness/runs",
                    {"mode": "implement", "task": "change files"},
                )
                self.assertEqual(status, HTTPStatus.BAD_REQUEST)
                self.assertEqual(body["error"], "write_mode_not_allowed")

                status, body = post_json_error(
                    f"{gateway.url}/v1/harness/runs",
                    {"mode": "plan", "task": "x", "surprise": True},
                )
                self.assertEqual(status, HTTPStatus.BAD_REQUEST)
                self.assertEqual(body["error"], "unsupported_run_fields")

    def test_private_mode_requires_access_token_file_when_constructed_directly(self):
        with tempfile.TemporaryDirectory() as tmp, fake_harness() as harness:
            token_file = Path(tmp) / "token"
            token_file.write_text(TOKEN, encoding="utf-8")
            config = GatewayConfig(
                harness_url=harness.url,
                token_file=token_file,
                private_bind_enabled=True,
                access_token_file=None,
            )
            with self.assertRaisesRegex(ConfigError, "access token"):
                GatewayHTTPServer(("127.0.0.1", 0), config)

    def test_private_mode_requires_gateway_auth_for_harness_api_only(self):
        with tempfile.TemporaryDirectory() as tmp, fake_harness() as harness:
            token_file = Path(tmp) / "token"
            access_file = Path(tmp) / "gateway-access"
            token_file.write_text(TOKEN, encoding="utf-8")
            create_gateway_access_token(access_file)
            access_token = access_file.read_text(encoding="utf-8").strip()
            config = GatewayConfig(
                harness_url=harness.url,
                token_file=token_file,
                private_bind_enabled=True,
                access_token_file=access_file,
            )
            with RunningGateway(config) as gateway:
                self.assertEqual(get_json(f"{gateway.url}/healthz")["ok"], True)
                status, body = get_json_error(f"{gateway.url}/v1/harness/readiness")
                self.assertEqual(status, HTTPStatus.UNAUTHORIZED)
                self.assertEqual(body["error"], "gateway_auth_required")
                status, body = get_json_error(
                    f"{gateway.url}/v1/harness/readiness",
                    {"Authorization": "Bearer wrong-token"},
                )
                self.assertEqual(status, HTTPStatus.FORBIDDEN)
                self.assertEqual(body["error"], "gateway_auth_failed")
                status, body = get_json_with_headers(
                    f"{gateway.url}/v1/harness/readiness",
                    {"Authorization": f"Bearer {access_token}"},
                )
                self.assertEqual(status, HTTPStatus.OK)
                self.assertEqual(body["overall"], "ready")


    def test_private_mode_exchanges_pair_token_for_mobile_session(self):
        with tempfile.TemporaryDirectory() as tmp, fake_harness() as harness:
            token_file = Path(tmp) / "token"
            access_file = Path(tmp) / "gateway-access"
            pair_file = Path(tmp) / "pair.json"
            token_file.write_text(TOKEN, encoding="utf-8")
            create_gateway_access_token(access_file)
            create_gateway_pairing_token(pair_file, ttl_seconds=60)
            pair_document = json.loads(pair_file.read_text(encoding="utf-8"))
            pair_token = pair_document["token"]
            config = GatewayConfig(
                harness_url=harness.url,
                token_file=token_file,
                private_bind_enabled=True,
                access_token_file=access_file,
                pair_token_file=pair_file,
            )
            with RunningGateway(config) as gateway:
                missing_status, missing_body = post_empty_error(f"{gateway.url}/v1/gateway/mobile-session")
                self.assertEqual(missing_status, HTTPStatus.UNAUTHORIZED)
                self.assertEqual(missing_body["error"], "gateway_auth_required")

                status, session = post_empty_with_headers(
                    f"{gateway.url}/v1/gateway/mobile-session",
                    {"Authorization": f"Bearer {pair_token}"},
                )
                self.assertEqual(status, HTTPStatus.CREATED)
                self.assertEqual(session["overall"], "ready")
                self.assertEqual(session["token_type"], "mobile_session")
                self.assertEqual(session["stored"], "server_memory_hash_only")
                self.assertEqual(session["client_storage"], "page_memory_only")
                self.assertEqual(session["pair_token_consumed"], True)
                self.assertFalse(pair_file.exists())
                self.assertNotIn(pair_token, json.dumps(session))
                session_token = str(session["session_token"])
                self.assertGreaterEqual(len(session_token), 32)

                status, body = get_json_with_headers(
                    f"{gateway.url}/v1/harness/readiness",
                    {"Authorization": f"Bearer {session_token}"},
                )
                self.assertEqual(status, HTTPStatus.OK)
                self.assertEqual(body["overall"], "ready")

                status, ops = get_json_with_headers(
                    f"{gateway.url}/v1/gateway/ops-status",
                    {"Authorization": f"Bearer {session_token}"},
                )
                self.assertEqual(status, HTTPStatus.OK)
                self.assertEqual(ops["mobile_session"]["overall"], "ready")
                self.assertEqual(ops["mobile_session"]["active_count"], 1)
                self.assertNotIn(session_token, json.dumps(ops))
                self.assertNotIn(pair_token, json.dumps(ops))

                status, revoked = delete_with_headers(
                    f"{gateway.url}/v1/gateway/mobile-session",
                    {"Authorization": f"Bearer {session_token}"},
                )
                self.assertEqual(status, HTTPStatus.OK)
                self.assertEqual(revoked["revoked"], True)
                self.assertNotIn(session_token, json.dumps(revoked))

                status, body = get_json_error(
                    f"{gateway.url}/v1/harness/readiness",
                    {"Authorization": f"Bearer {session_token}"},
                )
                self.assertEqual(status, HTTPStatus.FORBIDDEN)
                self.assertEqual(body["error"], "gateway_auth_failed")

                status, body = get_json_error(
                    f"{gateway.url}/v1/harness/readiness",
                    {"Authorization": f"Bearer {pair_token}"},
                )
                self.assertEqual(status, HTTPStatus.FORBIDDEN)
                self.assertEqual(body["error"], "gateway_auth_failed")

    def test_private_mode_rejects_pairing_token_for_direct_api_access(self):
        with tempfile.TemporaryDirectory() as tmp, fake_harness() as harness:
            token_file = Path(tmp) / "token"
            access_file = Path(tmp) / "gateway-access"
            pair_file = Path(tmp) / "pair.json"
            token_file.write_text(TOKEN, encoding="utf-8")
            create_gateway_access_token(access_file)
            create_gateway_pairing_token(pair_file, ttl_seconds=60)
            pair_token = json.loads(pair_file.read_text(encoding="utf-8"))["token"]
            config = GatewayConfig(
                harness_url=harness.url,
                token_file=token_file,
                private_bind_enabled=True,
                access_token_file=access_file,
                pair_token_file=pair_file,
            )
            with RunningGateway(config) as gateway:
                status, body = get_json_error(
                    f"{gateway.url}/v1/harness/readiness",
                    {"Authorization": f"Bearer {pair_token}"},
                )
                self.assertEqual(status, HTTPStatus.FORBIDDEN)
                self.assertEqual(body["error"], "gateway_auth_failed")

        with tempfile.TemporaryDirectory() as tmp, fake_harness() as harness:
            token_file = Path(tmp) / "token"
            access_file = Path(tmp) / "gateway-access"
            pair_file = Path(tmp) / "pair.json"
            token_file.write_text(TOKEN, encoding="utf-8")
            create_gateway_access_token(access_file)
            create_gateway_pairing_token(pair_file, ttl_seconds=60)
            pair_document = json.loads(pair_file.read_text(encoding="utf-8"))
            pair_document["expires_at"] = "2000-01-01T00:00:00Z"
            pair_file.write_text(json.dumps(pair_document), encoding="utf-8")
            pair_file.chmod(0o600)
            config = GatewayConfig(
                harness_url=harness.url,
                token_file=token_file,
                private_bind_enabled=True,
                access_token_file=access_file,
                pair_token_file=pair_file,
            )
            with RunningGateway(config) as gateway:
                status, body = get_json_error(
                    f"{gateway.url}/v1/harness/readiness",
                    {"Authorization": f"Bearer {pair_document['token']}"},
                )
                self.assertEqual(status, HTTPStatus.FORBIDDEN)
                self.assertEqual(body["error"], "gateway_auth_failed")


    def test_private_mode_missing_pairing_file_fails_closed_without_handler_crash(self):
        with tempfile.TemporaryDirectory() as tmp, fake_harness() as harness:
            token_file = Path(tmp) / "token"
            access_file = Path(tmp) / "gateway-access"
            pair_file = Path(tmp) / "missing-pair.json"
            token_file.write_text(TOKEN, encoding="utf-8")
            create_gateway_access_token(access_file)
            config = GatewayConfig(
                harness_url=harness.url,
                token_file=token_file,
                private_bind_enabled=True,
                access_token_file=access_file,
                pair_token_file=pair_file,
            )
            header_name = "".join(chr(c) for c in [65, 117, 116, 104, 111, 114, 105, 122, 97, 116, 105, 111, 110])
            with RunningGateway(config) as gateway:
                status, body = get_json_error(
                    f"{gateway.url}/v1/harness/readiness",
                    {header_name: ("Be" + "arer ") + "stale-pair-token-that-no-longer-exists"},
                )
                self.assertEqual(status, HTTPStatus.FORBIDDEN)
                self.assertEqual(body["error"], "gateway_auth_failed")

    def test_private_mode_rate_limits_repeated_auth_failures(self):
        with tempfile.TemporaryDirectory() as tmp, fake_harness() as harness:
            token_file = Path(tmp) / "token"
            access_file = Path(tmp) / "gateway-access"
            token_file.write_text(TOKEN, encoding="utf-8")
            create_gateway_access_token(access_file)
            config = GatewayConfig(
                harness_url=harness.url,
                token_file=token_file,
                private_bind_enabled=True,
                access_token_file=access_file,
            )
            with RunningGateway(config) as gateway:
                for _ in range(5):
                    status, body = get_json_error(
                        f"{gateway.url}/v1/harness/readiness",
                        {"Authorization": "Bearer wrong-token"},
                    )
                    self.assertEqual(status, HTTPStatus.FORBIDDEN)
                    self.assertEqual(body["error"], "gateway_auth_failed")
                status, body = get_json_error(
                    f"{gateway.url}/v1/harness/readiness",
                    {"Authorization": "Bearer still-wrong"},
                )
                self.assertEqual(status, HTTPStatus.TOO_MANY_REQUESTS)
                self.assertEqual(body["error"], "gateway_auth_rate_limited")

    def test_gateway_mvp_does_not_expose_raw_run_creation(self):
        with tempfile.TemporaryDirectory() as tmp, fake_harness() as harness:
            with RunningGateway(self._config(tmp, harness.url)) as gateway:
                request = Request(f"{gateway.url}/v1/runs", data=b"{}", method="POST")
                with self.assertRaises(HTTPError) as caught:
                    urlopen(request, timeout=5)
                self.assertEqual(caught.exception.code, HTTPStatus.METHOD_NOT_ALLOWED)


if __name__ == "__main__":
    unittest.main()
