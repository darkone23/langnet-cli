"""Backend tool fuzzing harness (CLI-driven).

This utility enumerates supported backend tools/actions and exercises them by
shelling out to the langnet CLI (`langnet-cli tool ...`). It can also fuzz the
unified `/api/q` endpoint (`langnet-cli query ...`) or run both paths for a
side-by-side comparison.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from collections.abc import Iterable, Sequence
from dataclasses import asdict, dataclass
from pathlib import Path

DEFAULT_SAVE_PATH = Path("examples/debug/fuzz_results")
FuzzMode = str


# Catalog of supported tools/actions with default word lists
TOOL_CATALOG: dict = {
    "diogenes": {
        "actions": {
            "parse": {
                "langs": ["lat", "grc"],
                "default_words": {
                    "lat": ["lupus", "arma", "vir", "amo", "sum", "video"],
                    "grc": ["logos", "anthropos", "agathos", "lego"],
                },
            },
        }
    },
    "whitakers": {
        "actions": {
            "search": {
                "langs": ["lat"],
                "default_words": {"lat": ["amo", "bellum", "lupus"]},
            }
        }
    },
    "heritage": {
        "actions": {
            "morphology": {"langs": ["san"], "default_words": {"san": ["agni", "yoga"]}},
            "canonical": {
                "langs": ["san"],
                "default_words": {"san": ["agnii", "agnim", "agnina", "agni", "veda", "krishna", "shiva"]},
            },
            # "lemmatize": {
            #     "langs": ["san"],
            #     "default_words": {"san": ["agnim", "yogena", "agnina"]},
            # },
        }
    },
    "cdsl": {
        "actions": {
            "lookup": {
                "langs": ["san"],
                "default_words": {"san": ["agni", "yoga", "deva"]},
                "dict_name": "mw",
                "compare_optional": True,
            }
        }
    },
    "cltk": {
        "actions": {
            "morphology": {
                "langs": ["lat", "grc", "san"],
                "default_words": {
                    "lat": ["amo", "sum"],
                    "grc": ["logos", "anthropos"],
                    "san": ["agni"],
                },
                "compare_optional": True,
            },
            "dictionary": {
                "langs": ["lat"],
                "default_words": {"lat": ["lupus", "arma", "amo"]},
                "compare_optional": True,
            },
        }
    },
}


@dataclass
class FuzzTarget:
    tool: str
    action: str
    lang: str | None
    word: str
    dict_name: str | None = None
    allow_empty: bool = False
    compare_optional: bool = False


@dataclass
class FuzzResult:
    target: FuzzTarget
    mode: FuzzMode
    tool_raw: dict | list | None
    tool_ok: bool | None
    tool_error: str | None
    tool_summary: dict | None
    unified_raw: list[dict] | dict | None
    unified_ok: bool | None
    unified_error: str | None
    unified_summary: dict | None
    unified_sources: list[str] | None
    source_present: bool | None

    def to_dict(self) -> dict:
        payload = {
            "target": asdict(self.target),
            "mode": self.mode,
            "tool_raw": self.tool_raw,
            "tool_ok": self.tool_ok,
            "tool_error": self.tool_error,
            "tool_summary": self.tool_summary,
            "unified_raw": self.unified_raw,
            "unified_ok": self.unified_ok,
            "unified_error": self.unified_error,
            "unified_summary": self.unified_summary,
            "unified_sources": self.unified_sources,
            "source_present": self.source_present,
        }
        return payload


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Fuzz backend tool or unified query outputs via API endpoints"
    )
    parser.add_argument(
        "--tool", help="Tool to exercise (diogenes, whitakers, heritage, cdsl, cltk)"
    )
    parser.add_argument("--action", help="Action/verb to use (search, parse, etc.)")
    parser.add_argument("--lang", help="Language code to use (lat, grc, san)")
    parser.add_argument("--words", help="Comma-separated list of words to test")
    parser.add_argument(
        "--validate",
        action="store_true",
        help="Mark run as failed when raw output is empty or raises an error",
    )
    parser.add_argument(
        "--mode",
        choices=["tool", "query", "compare"],
        default="tool",
        help=(
            "Fuzz mode: tool (only /api/tool/*), query (only /api/q), "
            "compare (tool plus unified comparison)"
        ),
    )
    parser.add_argument("--list", action="store_true", help="List available tool/actions and exit")
    parser.add_argument(
        "--save",
        nargs="?",
        const=str(DEFAULT_SAVE_PATH),
        help="Save results (directory for per-target files, default: examples/debug/fuzz_results)",
    )
    return parser.parse_args(argv)


def _iter_targets(
    selected_tool: str | None,
    selected_action: str | None,
    selected_lang: str | None,
    word_override: list[str] | None,
) -> Iterable[FuzzTarget]:
    for tool, tool_spec in TOOL_CATALOG.items():
        if selected_tool and tool != selected_tool:
            continue

        for action, action_spec in tool_spec["actions"].items():
            if selected_action and action != selected_action:
                continue

            langs = action_spec.get("langs") or [None]
            if selected_lang:
                langs = [selected_lang]

            for lang in langs:
                words = word_override or action_spec.get("default_words", {}).get(lang, []) or []
                if not words:
                    continue

                dict_name = action_spec.get("dict_name")
                allow_empty = action_spec.get("allow_empty", False)
                compare_optional = action_spec.get("compare_optional", False)
                for word in words:
                    yield FuzzTarget(
                        tool=tool,
                        action=action,
                        lang=lang,
                        word=word,
                        dict_name=dict_name,
                        allow_empty=allow_empty,
                        compare_optional=compare_optional,
                    )


def _summarize_raw(raw: dict | list | None) -> dict | None:
    if raw is None:
        return None

    if isinstance(raw, list):
        return {"items": len(raw)}

    if not isinstance(raw, dict):
        return {"type": type(raw).__name__}

    summary: dict[str, int] = {}
    for key, value in raw.items():
        try:
            summary[key] = len(value)  # type: ignore[arg-type]
        except Exception:
            summary[key] = 1
    return summary


def _run_cmd(cmd: Sequence[str]) -> str:
    result = subprocess.run(cmd, check=True, capture_output=True, text=True)
    return result.stdout.strip()


def _cli_tool_request(target: FuzzTarget) -> dict:
    """Invoke langnet-cli tool query and return parsed JSON."""
    cmd = [
        "langnet-cli",
        "tool",
        "query",
        "--tool",
        target.tool,
        "--action",
        target.action,
        "--query",
        target.word,
    ]
    if target.lang:
        cmd.extend(["--lang", target.lang])
    if target.dict_name:
        cmd.extend(["--dict", target.dict_name])

    stdout = _run_cmd(cmd)
    return json.loads(stdout) if stdout else {}


def _cli_unified_query(lang: str, word: str) -> list[dict]:
    """Invoke langnet-cli query and return parsed JSON."""
    cmd = ["langnet-cli", "query", lang, word, "--output", "json"]
    stdout = _run_cmd(cmd)
    return json.loads(stdout) if stdout else []


def _run_target(target: FuzzTarget, mode: FuzzMode, validate: bool) -> FuzzResult:
    tool_raw: dict | list | None = None
    tool_ok: bool | None = None
    tool_error: str | None = None
    tool_summary: dict | None = None
    unified_raw: list[dict] | dict | None = None
    unified_ok: bool | None = None
    unified_error: str | None = None
    unified_summary: dict | None = None
    unified_sources: list[str] | None = None
    source_present: bool | None = None

    if mode in ("tool", "compare"):
        try:
            tool_raw = _cli_tool_request(target)
            tool_summary = _summarize_raw(tool_raw)
            tool_ok = bool(tool_raw) or target.allow_empty or not validate
        except Exception as exc:  # noqa: BLE001
            tool_error = str(exc)
            tool_ok = False

    if mode in ("query", "compare") and target.lang:
        try:
            entries = _cli_unified_query(target.lang, target.word)
            unified_raw = entries
            unified_summary = _summarize_raw({"entries": entries})
            unified_ok = bool(entries) or target.allow_empty or not validate
            unified_sources = sorted(
                {entry.get("source") for entry in entries if entry.get("source")}
            )
            source_present = target.tool in unified_sources
            if target.compare_optional and not source_present:
                # Treat missing source as informational, not a failure
                source_present = None
        except Exception as exc:  # noqa: BLE001
            unified_error = str(exc)
            unified_ok = False

    return FuzzResult(
        target=target,
        mode=mode,
        tool_raw=tool_raw,
        tool_ok=tool_ok,
        tool_error=tool_error,
        tool_summary=tool_summary,
        unified_raw=unified_raw,
        unified_ok=unified_ok,
        unified_error=unified_error,
        unified_summary=unified_summary,
        unified_sources=unified_sources,
        source_present=source_present,
    )


def _print_catalog() -> None:
    print("Supported tools/actions:")
    for tool, tool_spec in TOOL_CATALOG.items():
        actions = tool_spec.get("actions", {})
        for action, action_spec in actions.items():
            langs = ",".join(action_spec.get("langs", [])) or "-"
            samples = []
            for lang, words in (action_spec.get("default_words") or {}).items():
                if not words:
                    continue
                samples.append(f"{lang}:{' / '.join(words)}")
            sample_str = "; ".join(samples) if samples else "-"
            print(f"  - {tool}:{action} | langs={langs} | samples={sample_str}")


def _safe_word(word: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "_", word.strip()) or "word"


def _save_results(save_path: Path, results: list[FuzzResult]) -> None:
    if save_path.suffix:  # treat as single file
        save_path.parent.mkdir(parents=True, exist_ok=True)
        payload = [r.to_dict() for r in results]
        save_path.write_text(json.dumps(payload, indent=2))
        print(f"Saved results to {save_path}")
        return

    # Directory mode: one file per target plus summary
    save_path.mkdir(parents=True, exist_ok=True)
    summary: list[dict] = []
    for r in results:
        lang_part = r.target.lang or "any"
        fname = f"{r.target.tool}_{r.target.action}_{lang_part}_{_safe_word(r.target.word)}.json"
        fpath = save_path / fname
        fpath.write_text(json.dumps(r.to_dict(), indent=2))
        summary.append(
            {
                "file": fname,
                "target": asdict(r.target),
                "mode": r.mode,
                "tool_ok": r.tool_ok,
                "tool_error": r.tool_error,
                "unified_ok": r.unified_ok,
                "unified_error": r.unified_error,
                "source_present": r.source_present,
                "unified_sources": r.unified_sources,
            }
        )

    (save_path / "summary.json").write_text(json.dumps(summary, indent=2))
    print(f"Saved {len(results)} per-target results to {save_path}/ (summary.json)")


def run_from_args(argv: list[str]) -> int:
    """Entry point callable from scripts or CLI."""
    args = _parse_args(argv)

    if args.list:
        _print_catalog()
        return 0

    word_override = None
    if args.words:
        word_override = [w.strip() for w in args.words.split(",") if w.strip()]

    targets = list(_iter_targets(args.tool, args.action, args.lang, word_override))
    if not targets:
        print("No targets matched the provided filters. Use --list to see options.")
        return 1

    results: list[FuzzResult] = []
    for target in targets:
        result = _run_target(target, mode=args.mode, validate=args.validate)
        results.append(result)
        status_parts = [f"{target.tool}:{target.action}:{target.lang}:{target.word}"]

        if args.mode in ("tool", "compare"):
            if result.tool_ok:
                status_parts.append("tool=ok")
            elif result.tool_ok is False:
                status_parts.append(
                    f"tool=error{'' if not result.tool_error else f' ({result.tool_error})'}"
                )
            else:
                status_parts.append("tool=skip")

        if args.mode in ("query", "compare"):
            if result.unified_error is not None:
                status_parts.append(f"query=error ({result.unified_error})")
            elif result.source_present is True:
                status_parts.append("query=has-source")
            elif result.source_present is False and target.compare_optional:
                status_parts.append("query=optional-missing")
            elif result.source_present is False:
                status_parts.append("query=missing")
            elif result.unified_ok:
                status_parts.append("query=ok")
            else:
                status_parts.append("query=skip")

        print(" -> ".join(status_parts))

    if args.save is not None:
        output_path = Path(args.save) if args.save else DEFAULT_SAVE_PATH
        _save_results(output_path, results)

    if not args.validate:
        return 0

    failures: list[FuzzResult] = []
    for r in results:
        if args.mode in ("tool", "compare") and r.tool_ok is False:
            failures.append(r)
            continue
        if args.mode in ("query", "compare") and r.unified_error:
            failures.append(r)
            continue
        if args.mode == "query" and r.unified_ok is False:
            failures.append(r)

    return 1 if failures else 0


def main() -> int:
    return run_from_args(sys.argv[1:])


if __name__ == "__main__":
    sys.exit(main())
