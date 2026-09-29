"""Small JSON preferences store for the Tkinter shell."""

import json
from pathlib import Path

import db


DEFAULTS = {
    "theme": "dark",
    "fullscreen": True,
    "sidebar_open": True,
}


def default_path():
    return db.default_path().with_name("settings.json")


def load(path=None):
    preferences = dict(DEFAULTS)
    path = Path(path) if path is not None else default_path()
    try:
        stored = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        return preferences
    if isinstance(stored, dict):
        for key in DEFAULTS:
            if key in stored and isinstance(stored[key], type(DEFAULTS[key])):
                preferences[key] = stored[key]
    return preferences


def save(preferences, path=None):
    path = Path(path) if path is not None else default_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    useful = {key: preferences.get(key, value) for key, value in DEFAULTS.items()}
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(useful, indent=2), encoding="utf-8")
    temporary.replace(path)
