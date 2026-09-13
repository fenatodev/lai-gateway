import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EXT_DIR = ROOT / "vscode" / "lai-chat-extension"


class VSCodeExtensionTest(unittest.TestCase):
    def test_lai_chat_extension_manifest_registers_chat_participant(self) -> None:
        manifest = json.loads((EXT_DIR / "package.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["name"], "lai-chat")
        self.assertEqual(manifest["publisher"], "fenatodev")
        self.assertEqual(manifest["main"], "./extension.js")
        self.assertIn("onChatParticipant:lai.assistant", manifest["activationEvents"])
        participants = manifest["contributes"]["chatParticipants"]
        self.assertEqual(participants[0]["id"], "lai.assistant")
        self.assertEqual(participants[0]["name"], "lai")
        command_names = {item["name"] for item in participants[0]["commands"]}
        self.assertEqual(command_names, {"health", "workbench"})

    def test_lai_chat_extension_is_loopback_and_read_only_by_default(self) -> None:
        manifest = json.loads((EXT_DIR / "package.json").read_text(encoding="utf-8"))
        gateway_setting = manifest["contributes"]["configuration"]["properties"]["lai.gatewayUrl"]
        self.assertEqual(gateway_setting["default"], "http://127.0.0.1:8787")
        source = (EXT_DIR / "extension.js").read_text(encoding="utf-8")
        self.assertIn("createChatParticipant", source)
        self.assertIn("/v1/gateway/health-report", source)
        self.assertIn("/v1/harness/runs", source)
        self.assertIn('mode: "plan"', source)
        self.assertNotIn("/v1/local-chat/runs", source)
        self.assertNotIn("0.0.0.0", source)
        self.assertNotIn("192.168.", source)
        self.assertNotIn("telegram-bot-token", source)


if __name__ == "__main__":
    unittest.main()
