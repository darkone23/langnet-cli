from __future__ import annotations

from pathlib import Path


def test_cli_justfile_forwards_variadic_args_as_positional_argv() -> None:
    text = Path("justfile").read_text(encoding="utf-8")

    assert text.startswith("set positional-arguments\n")
    assert "{{ args }}" not in text
    assert "{{ opts }}" not in text
    assert 'bash ./.justscripts/run-langnet-cli "$@"' in text
    assert 'just cli "$@"' not in text


def test_cli_runner_uses_venv_entrypoint_without_devenv_shell_for_normal_runtime() -> None:
    text = Path(".justscripts/run-langnet-cli").read_text(encoding="utf-8")

    assert ".devenv/state/venv/bin/langnet-cli" in text
    assert 'exec "${venv_cli}" "$@"' in text
    assert "devenv shell -- langnet-cli" in text


def test_web_justfile_forwards_cli_args_as_positional_argv() -> None:
    text = Path("../langnet-web2/justfile").read_text(encoding="utf-8")

    assert text.startswith("set positional-arguments\n")
    assert 'cd "{{cli_dir}}" && just cli "$@"' in text
    assert "just cli {{ args }}" not in text
