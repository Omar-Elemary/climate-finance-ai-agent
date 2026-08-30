import json
import logging
from pathlib import Path

from .base import Persona

logger = logging.getLogger(__name__)

_DEFAULT_DIR = Path(__file__).resolve().parent.parent.parent / "personas"


def load_persona(name: str, directory: str | Path | None = None) -> Persona:
    if directory is None:
        directory = _DEFAULT_DIR
    else:
        directory = Path(directory)

    json_path = directory / f"{name}.json"
    if not json_path.exists():
        raise FileNotFoundError(
            f"Persona '{name}' not found. Looked for: {json_path}\n"
            f"Available: {list_personas(directory)}"
        )

    logger.info("Loading persona from %s", json_path)
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    return Persona(
        name=data.get("name", name),
        description=data.get("description", ""),
        system_prompt=data.get("system_prompt", ""),
        tone=data.get("tone", ""),
        focus_areas=data.get("focus_areas", []),
        extra=data.get("extra", {}),
    )


def load_personas(
    names: list[str] | None = None,
    directory: str | Path | None = None,
) -> list[Persona]:
    if names is None:
        names = list_personas(directory)
    return [load_persona(n, directory) for n in names]


def list_personas(directory: str | Path | None = None) -> list[str]:
    if directory is None:
        directory = _DEFAULT_DIR
    else:
        directory = Path(directory)

    if not directory.exists():
        return []

    return sorted(p.stem for p in directory.glob("*.json"))
