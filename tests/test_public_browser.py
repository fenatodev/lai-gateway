import json
import subprocess
import sys
import unittest
from io import BytesIO
from urllib.error import HTTPError

from lai_gateway.public_browser import collect_public_browser, render_public_browser


class FakeResponse:
    status = 200
    code = 200
    headers = {"Content-Type": "text/html; charset=utf-8"}

    def __init__(self, body: bytes) -> None:
        self._body = BytesIO(body)
        self.closed = False

    def read(self, size: int = -1) -> bytes:
        return self._body.read(size)

    def close(self) -> None:
        self.closed = True


class PublicBrowserTest(unittest.TestCase):
    def test_plan_accepts_public_url_without_network_or_authority(self) -> None:
        payload = collect_public_browser(url="https://example.com/docs?q=lai", browser_action="plan")
        self.assertEqual(payload["overall"], "ready_to_fetch")
        self.assertFalse(payload["fetch_attempted"])
        self.assertFalse(payload["network_calls"])
        self.assertFalse(payload["executes_javascript"])
        self.assertFalse(payload["uses_cookies"])
        self.assertFalse(payload["grants_authority"])
        self.assertEqual(payload["schema_version"], "public-browser-read/v1")

    def test_fetch_uses_public_get_extracts_text_and_redacts_secret_shaped_content(self) -> None:
        calls = []

        def opener(request, timeout):
            calls.append((request.full_url, request.get_method(), timeout))
            body = b"<html><title>LAI page</title><script>bad()</script><p>Public text token=abc12345678901234567890</p></html>"
            return FakeResponse(body)

        payload = collect_public_browser(
            url="https://example.com/docs",
            browser_action="fetch",
            opener=opener,
            resolver=lambda host, port: ["93.184.216.34"],
        )
        self.assertEqual(payload["overall"], "ready")
        self.assertEqual(payload["status_code"], 200)
        self.assertEqual(calls[0][1], "GET")
        self.assertIn("LAI page", payload["title"])
        self.assertIn("Public text", payload["text_preview"])
        self.assertNotIn("bad()", payload["text_preview"])
        self.assertNotIn("abc12345678901234567890", json.dumps(payload))
        self.assertFalse(payload["security"]["executes_javascript"])
        self.assertFalse(payload["security"]["downloads_files"])
        self.assertFalse(payload["content_trusted"])

    def test_rejects_local_private_credentialed_secret_and_non_http_urls_before_network(self) -> None:
        samples = [
            "http://127.0.0.1:8000/",
            "http://localhost:8000/",
            "http://10.0.0.1/",
            "file:///etc/passwd",
            "https://user:pass@example.com/",
            "https://example.com/?api_key=abc12345678901234567890",
        ]
        for url in samples:
            payload = collect_public_browser(url=url, browser_action="fetch", opener=lambda *_a, **_k: None)
            self.assertEqual(payload["overall"], "blocked", url)
            self.assertFalse(payload["fetch_attempted"], url)
            self.assertFalse(payload["network_calls"], url)

    def test_dns_private_resolution_blocks_before_fetch(self) -> None:
        called = False

        def opener(*_args, **_kwargs):
            nonlocal called
            called = True
            return FakeResponse(b"ok")

        payload = collect_public_browser(
            url="https://safe.example/",
            browser_action="fetch",
            opener=opener,
            resolver=lambda host, port: ["192.168.1.9"],
        )
        self.assertEqual(payload["overall"], "blocked")
        self.assertEqual(payload["blocked_reason"], "dns_resolved_to_private_or_non_global_ip")
        self.assertFalse(called)

    def test_redirects_are_blocked_and_not_followed(self) -> None:
        def opener(request, timeout):
            raise HTTPError(request.full_url, 302, "Found", {"Location": "https://example.com/next"}, None)

        payload = collect_public_browser(
            url="https://example.com/redirect",
            browser_action="fetch",
            opener=opener,
            resolver=lambda host, port: ["93.184.216.34"],
        )
        self.assertEqual(payload["overall"], "blocked")
        self.assertEqual(payload["blocked_reason"], "http_error_or_redirect")
        self.assertFalse(payload["redirect_followed"])


    def test_inspect_public_source_extracts_links_without_following(self) -> None:
        calls = []

        def opener(request, timeout):
            calls.append((request.full_url, request.get_method(), timeout))
            body = b"""
            <html>
              <head>
                <title>LAI source</title>
                <meta name="description" content="safe description token=abc12345678901234567890">
              </head>
              <body>
                <h1>Primary heading</h1>
                <h2>Second heading</h2>
                <a href="/about">About</a>
                <a href="https://other.example/path?q=1">Other</a>
                <a href="http://127.0.0.1/admin">Local</a>
                <a href="javascript:alert(1)">Script</a>
                <a href="https://example.com/?api_key=abc12345678901234567890">Secret</a>
              </body>
            </html>
            """
            return FakeResponse(body)

        payload = collect_public_browser(
            url="https://example.com/docs/page",
            browser_action="inspect",
            opener=opener,
            resolver=lambda host, port: ["93.184.216.34"],
        )
        self.assertEqual(payload["overall"], "ready")
        self.assertEqual(payload["schema_version"], "public-browser-inspector/v1")
        self.assertEqual(calls, [("https://example.com/docs/page", "GET", 8.0)])
        self.assertTrue(payload["source_inspection_enabled"])
        self.assertTrue(payload["links_extracted"])
        self.assertFalse(payload["links_followed"])
        self.assertEqual(payload["link_count_total"], 5)
        self.assertEqual(payload["public_link_count_retained"], 2)
        self.assertEqual(payload["blocked_link_count"], 3)
        self.assertTrue(payload["security"]["links_validated_without_dns"])
        headings = [item["text"] for item in payload["headings"]]
        self.assertIn("Primary heading", headings)
        urls = [item["url"] for item in payload["public_links"]]
        self.assertIn("https://example.com/about", urls)
        self.assertIn("https://other.example/path?q=1", urls)
        self.assertNotIn("abc12345678901234567890", json.dumps(payload))
        self.assertFalse(payload["grants_authority"])

    def test_cli_public_browser_plan_is_secret_free(self) -> None:
        result = subprocess.run(
            [sys.executable, "-m", "lai_gateway", "public-browser", "--url", "https://example.com/path", "--json"],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True,
        )
        payload = json.loads(result.stdout)
        self.assertEqual(payload["operation"], "public-browser")
        self.assertFalse(payload["fetch_attempted"])
        self.assertNotIn("Bearer", result.stdout + result.stderr)

    def test_render_public_browser_is_bounded_and_explicit(self) -> None:
        payload = collect_public_browser(url="https://example.com/", browser_action="plan")
        rendered = render_public_browser(payload)
        self.assertIn("cookies: false", rendered)
        self.assertIn("javascript: false", rendered)
        self.assertIn("forms_submitted: false", rendered)
        self.assertIn("credentialed_access: false", rendered)


if __name__ == "__main__":
    unittest.main()
