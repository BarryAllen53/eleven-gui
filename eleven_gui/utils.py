from __future__ import annotations

import math
import mimetypes
from datetime import datetime
from pathlib import Path


def clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(maximum, value))


def format_count(value: int | float | None) -> str:
    if value is None:
        return "N/A"
    number = float(value)
    if abs(number) >= 1_000_000:
        return f"{number / 1_000_000:.2f}M"
    if abs(number) >= 1_000:
        return f"{number / 1_000:.1f}K"
    if math.isfinite(number) and number.is_integer():
        return f"{int(number):,}"
    return f"{number:,.2f}"


def format_percent(current: int | float | None, total: int | float | None) -> str:
    if current is None or total in (None, 0):
        return "N/A"
    value = (float(current) / float(total)) * 100
    return f"{value:.1f}%"


def format_unix(value: int | float | None) -> str:
    if not value:
        return "Unknown"
    return datetime.fromtimestamp(value).strftime("%d %b %Y %H:%M")


def parse_labels(text: str) -> dict[str, str]:
    result: dict[str, str] = {}
    for raw_part in text.split(","):
        part = raw_part.strip()
        if not part:
            continue
        if ":" in part:
            key, value = part.split(":", 1)
        elif "=" in part:
            key, value = part.split("=", 1)
        else:
            key, value = part, part
        key = key.strip()
        value = value.strip()
        if key:
            result[key] = value
    return result


def format_labels(labels: dict[str, str] | None) -> str:
    if not labels:
        return ""
    return ", ".join(f"{key}:{value}" for key, value in labels.items())


def content_type_to_suffix(content_type: str | None) -> str:
    if not content_type:
        return ".mp3"
    lower = content_type.lower()
    if "opus" in lower:
        return ".opus"
    if "pcm" in lower:
        return ".pcm"
    if "ulaw" in lower:
        return ".ulaw"
    if "alaw" in lower:
        return ".alaw"
    if "mpeg" in lower or "mp3" in lower:
        return ".mp3"
    if "wav" in lower:
        return ".wav"
    if "ogg" in lower:
        return ".ogg"
    guessed = mimetypes.guess_extension(lower.split(";")[0].strip())
    return guessed or ".bin"


def ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def timestamped_file(directory: Path, prefix: str, suffix: str) -> Path:
    ensure_dir(directory)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    return directory / f"{prefix}-{stamp}{suffix}"
