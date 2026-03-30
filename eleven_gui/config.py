from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parent.parent
APP_DIR_NAME = "ElevenGUI"


@dataclass(slots=True)
class AppConfig:
    project_root: Path
    assets_dir: Path
    outputs_dir: Path
    cache_dir: Path
    api_key: str
    api_key_source: str


def _is_packaged_runtime() -> bool:
    return bool(getattr(sys, "frozen", False) or "__compiled__" in globals())


def _runtime_root() -> Path:
    if _is_packaged_runtime():
        return Path(sys.argv[0]).resolve().parent
    return PROJECT_ROOT


def _assets_root() -> Path:
    if _is_packaged_runtime():
        return Path(__file__).resolve().parent / "assets"
    return PROJECT_ROOT / "eleven_gui" / "assets"


def _windows_path(env_name: str, default_parts: tuple[str, ...]) -> Path:
    env_value = os.getenv(env_name, "").strip()
    if env_value:
        return Path(env_value)
    return Path.home().joinpath(*default_parts)


def _user_config_root() -> Path:
    if os.name == "nt":
        return _windows_path("APPDATA", ("AppData", "Roaming")) / APP_DIR_NAME
    return Path.home() / ".config" / APP_DIR_NAME


def _user_state_root() -> Path:
    if os.name == "nt":
        return _windows_path("LOCALAPPDATA", ("AppData", "Local")) / APP_DIR_NAME
    return Path.home() / ".local" / "share" / APP_DIR_NAME


def _is_portable_packaged_runtime() -> bool:
    return _is_packaged_runtime() and (_runtime_root() / ".portable").exists()


def _config_root() -> Path:
    runtime_root = _runtime_root()
    if _is_packaged_runtime() and not _is_portable_packaged_runtime():
        return _user_config_root()
    return runtime_root


def _state_root() -> Path:
    runtime_root = _runtime_root()
    if _is_packaged_runtime() and not _is_portable_packaged_runtime():
        return _user_state_root()
    return runtime_root


def _api_key_candidates() -> list[tuple[Path, str]]:
    runtime_root = _runtime_root()
    config_root = _config_root()
    candidates = [
        (runtime_root / ".env", ".env"),
        (runtime_root / "api key.txt", "api key.txt"),
    ]
    if config_root != runtime_root:
        candidates.extend(
            [
                (config_root / ".env", "user profile .env"),
                (config_root / "api key.txt", "user profile api key.txt"),
            ]
        )
    return candidates


def load_config() -> AppConfig:
    runtime_root = _runtime_root()
    config_root = _config_root()
    state_root = _state_root()
    outputs_dir = state_root / "outputs"
    cache_dir = state_root / ".cache"
    outputs_dir.mkdir(parents=True, exist_ok=True)
    cache_dir.mkdir(parents=True, exist_ok=True)

    api_key = ""
    source = "missing"

    for key_file, label in _api_key_candidates():
        if not key_file.exists():
            continue
        if key_file.name == ".env":
            load_dotenv(key_file, override=False)
            env_key = os.getenv("ELEVENLABS_API_KEY", "").strip()
            if env_key:
                api_key = env_key
                source = label
                break
        else:
            legacy_key = key_file.read_text(encoding="utf-8").strip()
            if legacy_key:
                api_key = legacy_key
                source = label
                break

    return AppConfig(
        project_root=runtime_root,
        assets_dir=_assets_root(),
        outputs_dir=outputs_dir,
        cache_dir=cache_dir,
        api_key=api_key,
        api_key_source=source,
    )


def save_api_key(api_key: str) -> str:
    api_key = api_key.strip()
    config_root = _config_root()
    config_root.mkdir(parents=True, exist_ok=True)
    env_file = config_root / ".env"
    lines: list[str] = []

    if env_file.exists():
        lines = env_file.read_text(encoding="utf-8").splitlines()

    updated = False
    next_lines: list[str] = []
    for line in lines:
        if line.startswith("ELEVENLABS_API_KEY="):
            next_lines.append(f"ELEVENLABS_API_KEY={api_key}")
            updated = True
        else:
            next_lines.append(line)

    if not updated:
        if next_lines and next_lines[-1] != "":
            next_lines.append("")
        next_lines.append(f"ELEVENLABS_API_KEY={api_key}")

    env_file.write_text("\n".join(next_lines).strip() + "\n", encoding="utf-8")
    if config_root == _runtime_root():
        return ".env"
    return "user profile .env"


def mask_api_key(api_key: str) -> str:
    value = api_key.strip()
    if len(value) < 8:
        return "unset"
    return f"{value[:4]}...{value[-4:]}"
