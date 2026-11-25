import importlib.util
from pathlib import Path
import subprocess
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts/hyprland/special_workspaces.py"


class SpecialWorkspacesTests(unittest.TestCase):
    def render(self, entries):
        spec = importlib.util.spec_from_file_location("special_workspaces", SCRIPT)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module.render(entries)

    def test_media_and_scratchpad_generate_valid_lua(self):
        output = self.render([
            {"name": "Media", "toggleKeybind": "super + m", "moveKeybind": ""},
            {"name": "special", "toggleKeybind": "SUPER + S",
             "moveKeybind": "SUPER + SHIFT + S",
             "toggleAliases": "CTRL + SUPER + S, SUPER + mouse:275"},
        ])
        self.assertIn('hl.unbind("SUPER + M")', output)
        self.assertIn('hl.dsp.workspace.toggle_special("Media")', output)
        self.assertIn('workspace = "special:special", follow = false', output)
        self.assertIn('hl.unbind("SUPER + mouse:275")', output)
        checked = subprocess.run(["luac", "-p", "-"], input=output, text=True,
                                 capture_output=True)
        self.assertEqual(checked.returncode, 0, checked.stderr)

    def test_reject_duplicate_names_and_keybinds(self):
        for entries in [
            [{"name": "Media"}, {"name": "Media"}],
            [{"name": "Media", "toggleKeybind": "super + m"},
             {"name": "Other", "toggleKeybind": "SUPER + M"}],
            [{"name": "Media", "toggleKeybind": "SUPER + CTRL + M"},
             {"name": "Other", "moveKeybind": "CTRL + SUPER + m"}],
        ]:
            with self.subTest(entries=entries), self.assertRaises(ValueError):
                self.render(entries)

    def test_reject_unsafe_names_and_shortcuts(self):
        for entry in [{"name": "bad name"}, {"name": 'a"\nfoo'},
                      {"name": "special:Media"},
                      {"name": "Media", "toggleKeybind": "SUPER + X\nfoo"},
                      {"name": "Media", "toggleKeybind": "UNKNOWN + X"}]:
            with self.subTest(entry=entry), self.assertRaises(ValueError):
                self.render([entry])

    def test_empty_list_can_remove_all_managed_workspaces(self):
        self.assertNotIn("hl.bind(", self.render([]))

    def test_all_special_workspaces_get_scratchpad_margins(self):
        output = self.render([
            {"name": "media", "toggleKeybind": "SUPER + M"},
            {"name": "chat"},
        ])
        for name in ("media", "chat"):
            self.assertIn(
                f'hl.workspace_rule({{ workspace = "special:{name}", gaps_out = 30 }})',
                output,
            )


if __name__ == "__main__":
    unittest.main()
