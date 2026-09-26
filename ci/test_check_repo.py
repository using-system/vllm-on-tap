from pathlib import Path

from check_repo import check_presets, check_skills


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


def test_valid_skill_passes(tmp_path):
    write(tmp_path / "skills/vot-serve/SKILL.md", "---\nname: vot-serve\ndescription: Serve a preset.\n---\n# x\n")
    assert check_skills(tmp_path) == []


def test_skill_without_frontmatter_fails(tmp_path):
    write(tmp_path / "skills/vot-serve/SKILL.md", "# no frontmatter\n")
    assert check_skills(tmp_path) == ["skills/vot-serve/SKILL.md: no YAML frontmatter"]


def test_skill_name_must_match_directory(tmp_path):
    write(tmp_path / "skills/vot-serve/SKILL.md", "---\nname: serve\ndescription: d\n---\n")
    assert check_skills(tmp_path) == ["skills/vot-serve/SKILL.md: name 'serve' != directory 'vot-serve'"]


def test_skill_needs_description(tmp_path):
    write(tmp_path / "skills/vot-serve/SKILL.md", "---\nname: vot-serve\n---\n")
    assert check_skills(tmp_path) == ["skills/vot-serve/SKILL.md: missing description"]


def test_no_skills_directory_fails(tmp_path):
    assert check_skills(tmp_path) == ["skills/: no SKILL.md found"]


def test_preset_name_must_match_file(tmp_path):
    write(tmp_path / "presets/gemma.yaml", "name: other\nmodel: m\n")
    assert check_presets(tmp_path) == ["presets/gemma.yaml: name 'other' != file name 'gemma'"]


def test_valid_preset_passes(tmp_path):
    write(tmp_path / "presets/gemma.yaml", "name: gemma\nmodel: m\n")
    assert check_presets(tmp_path) == []
