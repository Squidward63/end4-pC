#!/usr/bin/env python3
"""Validate Settings workspace definitions and write their Hyprland Lua binds."""
import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile

NAME = re.compile(r"[\w-]{1,64}")
MODIFIERS = ("SUPER", "CTRL", "ALT", "SHIFT")


def lua_string(value):
    return json.dumps(value, ensure_ascii=False)


def shortcut(value):
    if not isinstance(value, str) or "\n" in value or "\r" in value:
        raise ValueError("Invalid shortcut: use e.g. SUPER + M")
    if not value.strip():
        return ""
    parts = [part.strip() for part in value.split("+")]
    mods, key = parts[:-1], parts[-1]
    mods = [mod.upper() for mod in mods]
    if any(mod not in MODIFIERS for mod in mods) or len(set(mods)) != len(mods):
        raise ValueError(f"Invalid modifiers in shortcut: {value}")
    if not re.fullmatch(r"(?:[A-Za-z0-9_]+|mouse:[0-9]+|code:[0-9]+)", key):
        raise ValueError(f"Invalid key in shortcut: {value}")
    if len(key) == 1:
        key = key.upper()
    return " + ".join([mod for mod in MODIFIERS if mod in mods] + [key])


def render(entries):
    if not isinstance(entries, list):
        raise ValueError("Workspaces must be a list")
    names, keys = set(), set()
    lines = ["-- Managed by end4-pC Settings > Special workspaces.\n"]
    for entry in entries:
        if not isinstance(entry, dict):
            raise ValueError("Invalid workspace entry")
        name = entry.get("name", "")
        if not isinstance(name, str) or not NAME.fullmatch(name):
            raise ValueError("Workspace names: 1–64 letters in any language, numbers, underscores or hyphens")
        if name in names:
            raise ValueError(f"Duplicate workspace name: {name}")
        names.add(name)
        lines.append(f'hl.workspace_rule({{ workspace = {lua_string("special:" + name)}, gaps_out = 30 }})')
        aliases = entry.get("toggleAliases", "")
        if not isinstance(aliases, str):
            raise ValueError("Additional shortcuts must be separated by commas")
        binds = [(entry.get("toggleKeybind", ""), False),
                 (entry.get("moveKeybind", ""), True)]
        binds.extend((alias, False) for alias in aliases.split(",") if alias.strip())
        for value, move in binds:
            key = shortcut(value)
            if not key:
                continue
            identity = key.lower()
            if identity in keys:
                raise ValueError(f"Duplicate shortcut: {key}")
            keys.add(identity)
            action = (f'hl.dsp.window.move({{ workspace = {lua_string("special:" + name)}, follow = false }})'
                      if move else f"hl.dsp.workspace.toggle_special({lua_string(name)})")
            description = f"Special workspace: {'Move window to' if move else 'Toggle'} {name}"
            lines.extend([f"hl.unbind({lua_string(key)})",
                          f"hl.bind({lua_string(key)}, {action}, {{ description = {lua_string(description)} }})"])
    return "\n".join(lines) + "\n"


def atomic_write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(dir=path.parent, prefix=".special-workspaces-")
    try:
        with os.fdopen(fd, "w") as handle:
            handle.write(text)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def apply(entries, path, reload=True):
    text = render(entries)  # Validate everything before touching the current config.
    previous = path.read_text() if path.exists() else None
    atomic_write(path, text)
    if not reload:
        return
    try:
        result = subprocess.run(["hyprctl", "reload"], capture_output=True, text=True)
        if result.returncode or result.stdout.strip() != "ok":
            raise ValueError(result.stderr.strip() or result.stdout.strip() or "Hyprland reload failed")
        errors = subprocess.run(["hyprctl", "configerrors"], capture_output=True, text=True)
        if errors.returncode or errors.stdout.strip():
            raise ValueError(errors.stdout.strip() or errors.stderr.strip() or "Could not check Hyprland config")
    except (OSError, ValueError):
        if previous is None:
            path.unlink(missing_ok=True)
        else:
            atomic_write(path, previous)
        subprocess.run(["hyprctl", "reload"], capture_output=True)
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--entries", required=True, help="JSON workspace list")
    parser.add_argument("--file", type=Path,
                        default=Path.home() / ".config/hypr/custom/special-workspaces.lua")
    parser.add_argument("--no-reload", action="store_true")
    args = parser.parse_args()
    try:
        apply(json.loads(args.entries), args.file, reload=not args.no_reload)
    except (ValueError, OSError) as error:
        print(str(error), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
