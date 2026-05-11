from __future__ import annotations

from pathlib import Path

DOCS_WITH_CURRENT_CLI_EXAMPLES = [
    Path("README.md"),
    Path("docs/GETTING_STARTED.md"),
    Path("docs/JUST_RECIPE_HEALTH.md"),
    Path("docs/OUTPUT_GUIDE.md"),
    Path("docs/plans/active/infra/local-lexicon-witness-handoff.md"),
    Path("docs/plans/active/pedagogy/learner-encounter-roadmap.md"),
]


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


def test_dev_tool_runner_uses_venv_entrypoint_without_devenv_shell_for_normal_runtime() -> None:
    text = Path(".justscripts/run-dev-tool").read_text(encoding="utf-8")

    assert ".devenv/state/venv/bin" in text
    assert 'exec "${venv_tool}" "$@"' in text
    assert "devenv shell -- true" in text


def test_routine_variadic_recipes_do_not_forward_args_through_devenv_shell() -> None:
    text = Path("justfile").read_text(encoding="utf-8")

    fragile_patterns = [
        'devenv shell -- nose2 -s tests --config tests/nose2.cfg "$@"',
        'devenv shell -- ruff format src/ tests/ ./.justscripts/ "$@"',
        'devenv shell -- ruff check src/ tests/ ./.justscripts "$@"',
        'devenv shell -- ty check src/ tests/ ./.justscripts "$@"',
        'devenv shell -- python3 .justscripts/autobot.py "$@"',
        'devenv shell -- python3 ./.justscripts/lex_translation_demo.py "$@"',
    ]
    for pattern in fragile_patterns:
        assert pattern not in text

    assert 'bash ./.justscripts/run-dev-tool nose2 -s tests --config tests/nose2.cfg "$@"' in text
    assert 'bash ./.justscripts/run-dev-tool ruff format src/ tests/ ./.justscripts/ "$@"' in text
    assert 'bash ./.justscripts/run-dev-tool ruff check src/ tests/ ./.justscripts "$@"' in text
    assert 'bash ./.justscripts/run-dev-tool ty check src/ tests/ ./.justscripts "$@"' in text
    assert 'bash ./.justscripts/run-dev-tool python3 .justscripts/autobot.py "$@"' in text
    assert (
        'bash ./.justscripts/run-dev-tool python3 ./.justscripts/lex_translation_demo.py "$@"'
        in text
    )


def test_cli_helper_recipes_use_langnet_cli_runner_not_inline_devenv_bash() -> None:
    text = Path("justfile").read_text(encoding="utf-8")

    assert "devenv shell -- bash -c 'langnet-cli parse" not in text
    assert "devenv shell -- bash -c 'langnet-cli triples-dump" not in text
    assert (
        'bash ./.justscripts/run-langnet-cli parse diogenes "$1" "$2" --opt "$3" '
        "--no-normalize --format json"
    ) in text
    assert (
        'bash ./.justscripts/run-langnet-cli parse "$1" "$2" "$3" --opt "$4" '
        "--no-normalize --format json"
    ) in text
    assert 'bash ./.justscripts/run-langnet-cli triples-dump "$1" "$2" "$3" --no-cache' in text


def test_current_docs_use_maintained_cli_wrapper_examples() -> None:
    fragile_pattern = "devenv shell -- bash -c 'langnet-cli"

    for path in DOCS_WITH_CURRENT_CLI_EXAMPLES:
        text = path.read_text(encoding="utf-8")
        assert fragile_pattern not in text, path


def test_web_justfile_forwards_cli_args_as_positional_argv() -> None:
    text = Path("../langnet-web2/justfile").read_text(encoding="utf-8")

    assert text.startswith("set positional-arguments\n")
    assert 'cd "{{cli_dir}}" && just cli "$@"' in text
    assert "just cli {{ args }}" not in text
