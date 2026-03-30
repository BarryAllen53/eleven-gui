from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parent.parent
ENV_FILE = PROJECT_ROOT / ".env"
LEGACY_KEY_FILE = PROJECT_ROOT / "api key.txt"


@dataclass(slots=True)
class AppConfig:
    project_root: Path
    assets_dir: Path
    outputs_dir: Path
    cache_dir: Path
    api_key: str
    api_key_source: str


def load_config() -> AppConfig:
    outputs_dir = PROJECT_ROOT / "outputs"
    cache_dir = PROJECT_ROOT / ".cache"
    outputs_dir.mkdir(exist_ok=True)
    cache_dir.mkdir(exist_ok=True)

    load_dotenv(ENV_FILE, override=False)
    api_key = ""
    source = "missing"

    env_key = os.getenv("ELEVENLABS_API_KEY", "").strip()
    if env_key:
        api_key = env_key
        source = ".env"
    elif LEGACY_KEY_FILE.exists():
        legacy_key = LEGACY_KEY_FILE.read_text(encoding="utf-8").strip()
        if legacy_key:
            api_key = legacy_key
            source = "api key.txt"

    return AppConfig(
        project_root=PROJECT_ROOT,
        assets_dir=PROJECT_ROOT / "eleven_gui" / "assets",
        outputs_dir=outputs_dir,
        cache_dir=cache_dir,
        api_key=api_key,
        api_key_source=source,
    )


def save_api_key(api_key: str) -> None:
    api_key = api_key.strip()
    lines: list[str] = []

    if ENV_FILE.exists():
        lines = ENV_FILE.read_text(encoding="utf-8").splitlines()

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

    ENV_FILE.write_text("\n".join(next_lines).strip() + "\n", encoding="utf-8")


def mask_api_key(api_key: str) -> str:
    value = api_key.strip()
    if len(value) < 8:
        return "unset"
    return f"{value[:4]}...{value[-4:]}"
