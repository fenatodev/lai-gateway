from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from lai_gateway.config import GatewayConfig
from tests.test_ui import RunningGateway, TOKEN, fake_harness, read_url


def post(
    url: str,
    payload: dict[str, object] | None = None,
) -> tuple[int, dict[str, object]]:
    data = None
    headers: dict[str, str] = {}

    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"

    request = Request(
        url,
        data=data,
        headers=headers,
        method="POST",
    )

    with urlopen(request, timeout=5) as response:
        return (
            response.status,
            json.loads(response.read().decode("utf-8")),
        )


def post_error(
    url: str,
    payload: dict[str, object],
) -> tuple[int, dict[str, object]]:
    request = Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        urlopen(request, timeout=5)
    except HTTPError as exc:
        return (
            exc.code,
            json.loads(exc.read().decode("utf-8")),
        )

    raise AssertionError("expected HTTPError")


class DirectConversationGatewayTest(unittest.TestCase):
    def _config(
        self,
        tmp: str,
        harness_url: str,
    ) -> GatewayConfig:
        token_file = Path(tmp) / "token"
        token_file.write_text(TOKEN, encoding="utf-8")

        return GatewayConfig(
            harness_url=harness_url,
            token_file=token_file,
        )

    def test_create_inspect_and_reset_direct_conversation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp, fake_harness() as harness:
            with RunningGateway(self._config(tmp, harness.url)) as gateway:
                status, created = post(
                    f"{gateway.url}/v1/gateway/conversations"
                )

                self.assertEqual(status, 201)

                conversation = created["conversation"]
                conversation_id = str(
                    conversation["conversation_id"]
                )

                self.assertTrue(
                    conversation_id.startswith("dc-")
                )
                self.assertFalse(
                    conversation["creates_harness_run"]
                )

                status, _, raw = read_url(
                    f"{gateway.url}/v1/gateway/conversations/"
                    f"{conversation_id}"
                )
                inspected = json.loads(raw)

                self.assertEqual(status, 200)
                self.assertEqual(
                    inspected["conversation"]["exchange_count"],
                    0,
                )

                status, reset = post(
                    f"{gateway.url}/v1/gateway/conversations/"
                    f"{conversation_id}/reset"
                )

                self.assertEqual(status, 200)
                self.assertEqual(
                    reset["conversation"]["exchange_count"],
                    0,
                )

    def test_second_turn_receives_first_exchange_as_history(self) -> None:
        with tempfile.TemporaryDirectory() as tmp, fake_harness() as harness:
            with RunningGateway(self._config(tmp, harness.url)) as gateway:
                _, created = post(
                    f"{gateway.url}/v1/gateway/conversations"
                )
                conversation_id = str(
                    created["conversation"]["conversation_id"]
                )

                with patch(
                    "lai_gateway.server.collect_model_chat"
                ) as collect:
                    collect.side_effect = (
                        {
                            "operation": "model-chat",
                            "overall": "ready",
                            "message": "resposta um",
                            "conversation": {
                                "creates_harness_run": False,
                            },
                            "security": {
                                "creates_harness_run": False,
                            },
                        },
                        {
                            "operation": "model-chat",
                            "overall": "ready",
                            "message": "resposta dois",
                            "conversation": {
                                "creates_harness_run": False,
                            },
                            "security": {
                                "creates_harness_run": False,
                            },
                        },
                    )

                    post(
                        f"{gateway.url}/v1/gateway/chat",
                        {
                            "message": "primeira",
                            "conversation_id": conversation_id,
                        },
                    )

                    _, second = post(
                        f"{gateway.url}/v1/gateway/chat",
                        {
                            "message": "segunda",
                            "conversation_id": conversation_id,
                        },
                    )

        self.assertEqual(
            collect.call_args_list[0].kwargs["history"],
            (),
        )
        self.assertEqual(
            collect.call_args_list[1].kwargs["history"],
            (
                {"role": "user", "content": "primeira"},
                {"role": "assistant", "content": "resposta um"},
            ),
        )
        self.assertEqual(
            second["conversation"]["exchange_count"],
            2,
        )
        self.assertFalse(
            second["conversation"]["creates_harness_run"]
        )
        self.assertFalse(
            second["security"]["history_is_authorization"]
        )
        self.assertTrue(
            second["security"]["stores_prompt"]
        )
        self.assertTrue(
            second["security"]["stores_prompt_in_memory"]
        )
        self.assertFalse(
            second["security"]["persistent_prompt_storage"]
        )

    def test_unknown_and_malformed_ids_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp, fake_harness() as harness:
            with RunningGateway(self._config(tmp, harness.url)) as gateway:
                status, body = post_error(
                    f"{gateway.url}/v1/gateway/chat",
                    {
                        "message": "teste",
                        "conversation_id": "invalid",
                    },
                )

                self.assertEqual(status, 400)
                self.assertEqual(
                    body["error"],
                    "invalid_direct_conversation_id",
                )

                status, body = post_error(
                    f"{gateway.url}/v1/gateway/chat",
                    {
                        "message": "teste",
                        "conversation_id": "dc-0000000000000000",
                    },
                )

                self.assertEqual(status, 404)
                self.assertEqual(
                    body["error"],
                    "direct_conversation_not_found",
                )

    def test_one_shot_chat_still_works_without_conversation_id(self) -> None:
        with tempfile.TemporaryDirectory() as tmp, fake_harness() as harness:
            with patch(
                "lai_gateway.server.collect_model_chat"
            ) as collect:
                collect.return_value = {
                    "operation": "model-chat",
                    "overall": "ready",
                    "message": "ok",
                    "security": {
                        "creates_harness_run": False,
                    },
                }

                with RunningGateway(
                    self._config(tmp, harness.url)
                ) as gateway:
                    status, _, _ = read_url(
                        f"{gateway.url}/v1/gateway/chat",
                        data=json.dumps(
                            {"message": "compatibilidade"}
                        ).encode("utf-8"),
                        method="POST",
                    )

        self.assertEqual(status, 200)
        collect.assert_called_once_with(
            prompt="compatibilidade",
            timeout_seconds=60.0,
            max_tokens=768,
        )


if __name__ == "__main__":
    unittest.main()
