from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from lai_gateway.config import GatewayConfig, read_control_token, read_gateway_access_token
from lai_gateway.errors import ConfigError


class ConfigTest(unittest.TestCase):
    def test_env_config_is_loopback_only_and_secret_free(self):
        config = GatewayConfig.from_env(
            {
                "LAI_GATEWAY_HARNESS_URL": "http://127.0.0.1:8765",
                "LAI_GATEWAY_TOKEN_FILE": "/tmp/token",
                "LAI_GATEWAY_BIND": "localhost",
                "LAI_GATEWAY_PORT": "8787",
            }
        )
        public = config.public_dict()
        self.assertEqual(public["harness_url"], "http://127.0.0.1:8765")
        self.assertEqual(public["bind"], "localhost")
        self.assertEqual(public["access_mode"], "loopback")
        self.assertIsNone(public["access_token_file"])
        self.assertNotIn("Bearer", repr(public))

    def test_rejects_non_loopback_harness_and_gateway_bind(self):
        with self.assertRaisesRegex(ConfigError, "loopback"):
            GatewayConfig.from_env({"LAI_GATEWAY_HARNESS_URL": "http://192.168.1.10:8765"})
        with self.assertRaisesRegex(ConfigError, "loopback"):
            GatewayConfig.from_env({"LAI_GATEWAY_BIND": "0.0.0.0"})
        with self.assertRaisesRegex(ConfigError, "wildcard"):
            GatewayConfig.from_env({"LAI_GATEWAY_BIND": "0.0.0.0", "LAI_GATEWAY_PRIVATE_BIND": "1"})
        with self.assertRaisesRegex(ConfigError, "public"):
            GatewayConfig.from_env({"LAI_GATEWAY_BIND": "8.8.8.8", "LAI_GATEWAY_PRIVATE_BIND": "1"})

    def test_private_bind_requires_explicit_flag_and_token_file_path(self):
        config = GatewayConfig.from_env(
            {
                "LAI_GATEWAY_BIND": "192.168.1.20",
                "LAI_GATEWAY_PRIVATE_BIND": "1",
                "LAI_GATEWAY_ACCESS_TOKEN_FILE": "/tmp/gateway-access",
            }
        )
        public = config.public_dict()
        self.assertEqual(public["bind"], "192.168.1.20")
        self.assertEqual(public["access_mode"], "private-token")
        self.assertEqual(public["access_token_file"], "/tmp/gateway-access")
        self.assertNotIn("secret", repr(public).lower())

    def test_reads_single_token_without_whitespace(self):
        with tempfile.TemporaryDirectory() as tmp:
            token_file = Path(tmp) / "token"
            token_file.write_text("abc123\n", encoding="utf-8")
            self.assertEqual(read_control_token(token_file), "abc123")
            token_file.write_text("abc 123\n", encoding="utf-8")
            with self.assertRaisesRegex(ConfigError, "whitespace"):
                read_control_token(token_file)
            token_file.write_text("short\n", encoding="utf-8")
            with self.assertRaisesRegex(ConfigError, "at least 16"):
                read_gateway_access_token(token_file)
            token_file.write_text("gateway-access-token\n", encoding="utf-8")
            self.assertEqual(read_gateway_access_token(token_file), "gateway-access-token")


if __name__ == "__main__":
    unittest.main()
