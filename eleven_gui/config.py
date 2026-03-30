from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parent.parent


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


def load_config() -> AppConfig:
    runtime_root = _runtime_root()
    env_file = runtime_root / ".env"
    legacy_key_file = runtime_root / "api key.txt"
    outputs_dir = runtime_root / "outputs"
    cache_dir = runtime_root / ".cache"
    outputs_dir.mkdir(exist_ok=True)
    cache_dir.mkdir(exist_ok=True)

    load_dotenv(env_file, override=False)
    api_key = ""
    source = "missing"

    env_key = os.getenv("ELEVENLABS_API_KEY", "").strip()
    if env_key:
        api_key = env_key
        source = ".env"
    elif legacy_key_file.exists():
        legacy_key = legacy_key_file.read_text(encoding="utf-8").strip()
        if legacy_key:
            api_key = legacy_key
            source = "api key.txt"

    return AppConfig(
        project_root=runtime_root,
        assets_dir=_assets_root(),
        outputs_dir=outputs_dir,
        cache_dir=cache_dir,
        api_key=api_key,
        api_key_source=source,
    )


def save_api_key(api_key: str) -> None:
    api_key = api_key.strip()
    env_file = _runtime_root() / ".env"
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


def mask_api_key(api_key: str) -> str:
    value = api_key.strip()
    if len(value) < 8:
        return "unset"
    return f"{value[:4]}...{value[-4:]}"
