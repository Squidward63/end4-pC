import json
import os
from pathlib import Path
import runpy
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch


SCRIPT = Path(__file__).resolve().parents[1] / "scripts/hyprland/autostart.py"


class AutostartTests(unittest.TestCase):
    def launch(self, apps):
        with tempfile.TemporaryDirectory() as home:
            config = Path(home) / ".config/illogical-impulse/config.json"
            config.parent.mkdir(parents=True)
            config.write_text(json.dumps({"hyprland": {"autostartApps": {
                "enable": True, "apps": apps,
            }}}))
            with patch.dict(os.environ, {"HOME": home}), \
                    patch.object(sys, "argv", [str(SCRIPT), "--force"]), \
                    patch("subprocess.run", return_value=subprocess.CompletedProcess(
                        [], 0, stdout='{"id": 3}'
                    )) as run, patch("time.sleep"):
                runpy.run_path(str(SCRIPT), run_name="__main__")
            return [call.args[0][2] for call in run.call_args_list
                    if call.args[0][1] == "dispatch"]

    def test_special_app_uses_scratchpad_without_focusing_it(self):
        commands = self.launch([{"cmd": "kitty", "workspace": 5, "specialWorkspace": True}])
        self.assertEqual(commands, [
            'hl.dsp.exec_cmd("kitty", {workspace = "special:special silent"})',
            'hl.dsp.focus({workspace = 3})',
        ])

    def test_existing_numbered_workspace_still_works(self):
        commands = self.launch([{"cmd": "firefox", "workspace": 5}])
        self.assertEqual(commands, [
            'hl.dsp.focus({workspace = 5})',
            'hl.dsp.exec_cmd("firefox")',
            'hl.dsp.focus({workspace = 3})',
        ])

    def test_mixed_entries_keep_their_destinations(self):
        commands = self.launch([
            {"cmd": "kitty", "specialWorkspace": True},
            {"cmd": "firefox", "workspace": 2, "specialWorkspace": False},
            {"cmd": " ", "specialWorkspace": True},
        ])
        self.assertEqual(commands, [
            'hl.dsp.exec_cmd("kitty", {workspace = "special:special silent"})',
            'hl.dsp.focus({workspace = 2})',
            'hl.dsp.exec_cmd("firefox")',
            'hl.dsp.focus({workspace = 3})',
        ])


if __name__ == "__main__":
    unittest.main()
