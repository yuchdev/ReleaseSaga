from pathlib import Path

import pytest

from release_saga import cli


def write_project(project_dir: Path, name: str = "demo-package") -> None:
    (project_dir / "src" / name.replace("-", "_")).mkdir(parents=True)
    (project_dir / "pyproject.toml").write_text(
        f"""
[project]
name = "{name}"
version = "1.2.3"
""".strip()
        + "\n",
        encoding="utf-8",
    )


def test_help_lists_release_flags(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exc_info:
        cli.main(["--help"])

    assert exc_info.value.code == 0
    help_text = capsys.readouterr().out
    assert "--project-dir" in help_text
    assert "--wheel-glob" in help_text
    assert "--s3-bucket" in help_text
    assert "--git-tag-template" in help_text
    assert "--release-notes-path" in help_text


def test_cli_uses_explicit_project_dir(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    project_dir = tmp_path / "target-project"
    write_project(project_dir)
    captured: list[Path] = []

    monkeypatch.setattr(cli, "sanity_check", lambda config: None)
    monkeypatch.setattr(cli, "build_wheel", lambda config: captured.append(config.project_dir))

    exit_code = cli.main(["--mode", "build", "--project-dir", str(project_dir)])

    assert exit_code == 0
    assert captured == [project_dir.resolve()]
