"""Repository checks CI runs next to the JSON Schema validations."""

import sys
from pathlib import Path

import yaml


def _frontmatter(text: str) -> dict | None:
    if not text.startswith("---\n"):
        return None
    end = text.find("\n---", 4)
    if end == -1:
        return None
    data = yaml.safe_load(text[4:end])
    return data if isinstance(data, dict) else None


def check_skills(root: Path) -> list[str]:
    files = sorted((root / "skills").glob("*/SKILL.md"))
    if not files:
        return ["skills/: no SKILL.md found"]
    errors = []
    for path in files:
        rel = path.relative_to(root).as_posix()
        meta = _frontmatter(path.read_text())
        if meta is None:
            errors.append(f"{rel}: no YAML frontmatter")
            continue
        directory = path.parent.name
        if meta.get("name") != directory:
            errors.append(f"{rel}: name '{meta.get('name')}' != directory '{directory}'")
        if not meta.get("description"):
            errors.append(f"{rel}: missing description")
    return errors


def check_presets(root: Path) -> list[str]:
    errors = []
    for path in sorted((root / "presets").glob("*.yaml")):
        data = yaml.safe_load(path.read_text()) or {}
        if data.get("name") != path.stem:
            errors.append(
                f"{path.relative_to(root).as_posix()}: name '{data.get('name')}' != file name '{path.stem}'"
            )
    return errors


def main() -> None:
    root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(".")
    errors = check_skills(root) + check_presets(root)
    for error in errors:
        print(error)
    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()
