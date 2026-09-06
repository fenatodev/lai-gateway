from __future__ import annotations

import json
import socket
import subprocess
import sys
import tempfile
import threading
import unittest
from pathlib import Path

from lai_gateway.errors import ConfigError
from lai_gateway.proxy import collect_mobile_proxy_status, validate_mobile_proxy_config


def free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


class TinyHTTPServer:
    def __init__(self) -> None:
        self.port = free_port()
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._serve, daemon=True)

    def __enter__(self) -> "TinyHTTPServer":
        self._thread.start()
        return self

    def __exit__(self, *exc: object) -> None:
        self._stop.set()
        try:
            with socket.create_connection(("127.0.0.1", self.port), timeout=1):
                pass
        except OSError:
            pass
        self._thread.join(timeout=5)

    def _serve(self) -> None:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
            server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            server.bind(("127.0.0.1", self.port))
            server.listen(16)
            server.settimeout(0.2)
            while not self._stop.is_set():
                try:
                    conn, _addr = server.accept()
                except TimeoutError:
                    continue
                with conn:
                    try:
                        conn.recv(4096)
                        conn.sendall(b"HTTP/1.1 200 OK\r\nContent-Length: 2\r\nConnection: close\r\n\r\nOK")
                    except OSError:
                        pass


class MobileProxyTest(unittest.TestCase):
    def test_config_rejects_non_loopback_listen_or_public_target(self) -> None:
        with self.assertRaises(ConfigError):
            validate_mobile_proxy_config(
                listen_host="0.0.0.0",
                listen_port=18787,
                target_host="127.0.0.1",
                target_port=8787,
            )
        with self.assertRaises(ConfigError):
            validate_mobile_proxy_config(
                listen_host="127.0.0.1",
                listen_port=18787,
                target_host="8.8.8.8",
                target_port=8787,
            )

    def test_collect_status_is_read_only_and_secret_free(self) -> None:
        with TinyHTTPServer() as target:
            payload = collect_mobile_proxy_status(
                listen_host="127.0.0.1",
                listen_port=free_port(),
                target_host="127.0.0.1",
                target_port=target.port,
            )
        body = json.dumps(payload)
        self.assertEqual(payload["operation"], "mobile-proxy")
        self.assertEqual(payload["overall"], "ready_to_start")
        self.assertFalse(payload["starts_server"])
        self.assertFalse(payload["modifies_files"])
        self.assertFalse(payload["security"]["payload_logging"])
        self.assertNotIn("Bearer", body)
        self.assertNotIn("token", body.lower().replace("tokens", ""))

    def test_cli_check_json_is_secret_free(self) -> None:
        repo = Path(__file__).parents[1]
        with TinyHTTPServer() as target:
            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "lai_gateway",
                    "mobile-proxy",
                    "--check",
                    "--json",
                    "--listen-port",
                    str(free_port()),
                    "--target-host",
                    "127.0.0.1",
                    "--target-port",
                    str(target.port),
                ],
                cwd=repo,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=True,
                timeout=10,
            )
        payload = json.loads(result.stdout)
        self.assertEqual(payload["overall"], "ready_to_start")
        self.assertNotIn("Bearer", result.stdout + result.stderr)

    def test_cli_check_reports_ready_when_proxy_is_already_running(self) -> None:
        repo = Path(__file__).parents[1]
        listen_port = free_port()
        with TinyHTTPServer() as target:
            proc = subprocess.Popen(
                [
                    sys.executable,
                    "-m",
                    "lai_gateway",
                    "mobile-proxy",
                    "--listen-port",
                    str(listen_port),
                    "--target-host",
                    "127.0.0.1",
                    "--target-port",
                    str(target.port),
                ],
                cwd=repo,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            try:
                assert proc.stdout is not None
                self.assertEqual(proc.stdout.readline().strip(), "lai-gateway mobile-proxy: ready")
                result = subprocess.run(
                    [
                        sys.executable,
                        "-m",
                        "lai_gateway",
                        "mobile-proxy",
                        "--check",
                        "--json",
                        "--listen-port",
                        str(listen_port),
                        "--target-host",
                        "127.0.0.1",
                        "--target-port",
                        str(target.port),
                    ],
                    cwd=repo,
                    text=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    check=True,
                    timeout=10,
                )
                payload = json.loads(result.stdout)
                self.assertEqual(payload["overall"], "ready")
                self.assertFalse(payload["checks"]["listen_available"]["ok"])
                self.assertTrue(payload["checks"]["listen_http"]["ok"])
                self.assertNotIn("Bearer", result.stdout + result.stderr)
            finally:
                proc.terminate()
                try:
                    proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    proc.wait(timeout=5)
                if proc.stdout is not None:
                    proc.stdout.close()
                if proc.stderr is not None:
                    proc.stderr.close()

    def test_proxy_forwards_http_without_payload_logging(self) -> None:
        repo = Path(__file__).parents[1]
        listen_port = free_port()
        with TinyHTTPServer() as target:
            proc = subprocess.Popen(
                [
                    sys.executable,
                    "-m",
                    "lai_gateway",
                    "mobile-proxy",
                    "--listen-port",
                    str(listen_port),
                    "--target-host",
                    "127.0.0.1",
                    "--target-port",
                    str(target.port),
                ],
                cwd=repo,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            try:
                assert proc.stdout is not None
                first = proc.stdout.readline().strip()
                self.assertEqual(first, "lai-gateway mobile-proxy: ready")
                with socket.create_connection(("127.0.0.1", listen_port), timeout=5) as client:
                    client.sendall(b"GET /healthz HTTP/1.1\r\nHost: local\r\nConnection: close\r\n\r\n")
                    data = client.recv(4096)
                self.assertIn(b"200 OK", data)
                self.assertIn(b"OK", data)
                stdout_so_far = proc.stdout.readline().strip()
                self.assertNotIn("GET /healthz", first + stdout_so_far)
            finally:
                proc.terminate()
                try:
                    proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    proc.wait(timeout=5)
                if proc.stdout is not None:
                    proc.stdout.close()
                if proc.stderr is not None:
                    proc.stderr.close()


if __name__ == "__main__":
    unittest.main()
