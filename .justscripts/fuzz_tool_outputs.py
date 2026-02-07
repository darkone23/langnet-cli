"""Backend tool fuzzing harness (CLI-driven).

This utility enumerates supported backend tools/actions and exercises them by
shelling out to the langnet CLI (`langnet-cli tool ...`). Optionally, it checks
that the unified `langnet-cli query` response contains the backend source.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable, List, Sequence

DEFAULT_SAVE_PATH = Path("examples/debug/fuzz_results")


# Catalog of supported tools/actions with default word lists
TOOL_CATALOG: dict = {
    "diogenes": {
        "actions": {
            "search": {
                "langs": ["lat", "grc"],
                "default_words": {
                    "lat": ["lupus", "arma", "vir", "amo"],
                    "grc": ["logos", "anthropos", "agathos"],
                },
            },
            "parse": {
                "langs": ["lat", "grc"],
                "default_words": {"lat": ["amo", "sum", "video"], "grc": ["lego", "anthropos"]},
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
            "analyze": {"langs": ["san"], "default_words": {"san": ["agni"]}},
            "search": {"langs": ["san"], "default_words": {"san": ["agni", "veda"]}},
            "canonical": {"langs": ["san"], "default_words": {"san": ["agnii", "agnim", "agnina"]}},
            "lemmatize": {"langs": ["san"], "default_words": {"san": ["agnim", "yogena", "agnina"]}},
            # Entry URLs are backend-specific; use only when you have a known path.
            "entry": {
                "langs": ["san"],
                "default_words": {"san": ["/skt/MW/890.html#agni", "/skt/AP90/125.html#agni"]},
                "allow_empty": True,
                "compare_optional": True,
            },
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
                "default_words": {"lat": ["amo", "sum"], "grc": ["logos", "anthropos"], "san": ["agni"]},
                "compare_optional": True,
            },
            "parse": {
                "langs": ["lat", "grc", "san"],
                "default_words": {"lat": ["sum", "video"], "grc": ["anthropos", "lego"], "san": ["yoga"]},
                "compare_optional": True,
            },
            "dictionary": {
                "langs": ["lat"],
                "default_words": {"lat": ["lupus", "arma"]},
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
    raw_ok: bool
    raw_error: str | None
    raw_summary: dict | None
    unified_sources: list[str] | None
    source_present: bool | None
    compare_error: str | None

    def to_dict(self) -> dict:
        payload = {
            "target": asdict(self.target),
            "raw_ok": self.raw_ok,
            "raw_error": self.raw_error,
            "raw_summary": self.raw_summary,
            "unified_sources": self.unified_sources,
            "source_present": self.source_present,
            "compare_error": self.compare_error,
        }
        return payload


def _parse_args(argv: List[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Fuzz backend tool outputs via API endpoints")
    parser.add_argument("--tool", help="Tool to exercise (diogenes, whitakers, heritage, cdsl, cltk)")
    parser.add_argument("--action", help="Action/verb to use (search, parse, etc.)")
    parser.add_argument("--lang", help="Language code to use (lat, grc, san)")
    parser.add_argument("--words", help="Comma-separated list of words to test")
    parser.add_argument(
        "--validate",
        action="store_true",
        help="Mark run as failed when raw output is empty or raises an error",
    )
    parser.add_argument(
        "--compare",
        action="store_true",
        help="Compare unified query results to see if the backend source is present",
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


def _summarize_raw(raw: dict | None) -> dict | None:
    if raw is None:
        return None

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


def _run_target(target: FuzzTarget, compare: bool, validate: bool) -> FuzzResult:
    raw_ok = False
    raw_error: str | None = None
    raw_summary: dict | None = None
    unified_sources: list[str] | None = None
    source_present: bool | None = None
    compare_error: str | None = None

    try:
        raw_data = _cli_tool_request(target)
        raw_summary = _summarize_raw(raw_data)
        raw_ok = bool(raw_data) or target.allow_empty or not validate
    except Exception as exc:  # noqa: BLE001
        raw_error = str(exc)
        raw_ok = False

    if compare and target.lang:
        try:
            entries = _cli_unified_query(target.lang, target.word)
            unified_sources = sorted({entry.get("source") for entry in entries if entry.get("source")})
            source_present = target.tool in unified_sources
            if target.compare_optional and not source_present:
                # Treat missing source as informational, not a failure
                source_present = None
        except Exception as exc:  # noqa: BLE001
            compare_error = str(exc)

    return FuzzResult(
        target=target,
        raw_ok=raw_ok,
        raw_error=raw_error,
        raw_summary=raw_summary,
        unified_sources=unified_sources,
        source_present=source_present,
        compare_error=compare_error,
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
                "raw_ok": r.raw_ok,
                "raw_error": r.raw_error,
                "compare_error": r.compare_error,
                "source_present": r.source_present,
                "unified_sources": r.unified_sources,
            }
        )

    (save_path / "summary.json").write_text(json.dumps(summary, indent=2))
    print(f"Saved {len(results)} per-target results to {save_path}/ (summary.json)")


def run_from_args(argv: List[str]) -> int:
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
        result = _run_target(target, compare=args.compare, validate=args.validate)
        results.append(result)
        compare_note = ""
        if args.compare:
            if result.compare_error is not None:
                compare_note = f" compare_error={result.compare_error}"
            elif result.source_present is True:
                compare_note = " compare=ok"
            elif result.source_present is False and target.compare_optional:
                compare_note = " compare=optional-missing"
            elif result.source_present is False:
                compare_note = " compare=missing"
            else:
                compare_note = " compare=skip"
        print(
            f"{target.tool}:{target.action}:{target.lang}:{target.word} -> "
            f"raw={'ok' if result.raw_ok else 'error'}"
            f"{'' if not result.raw_error else f' ({result.raw_error})'}"
            f"{compare_note}"
        )

    if args.save is not None:
        output_path = Path(args.save) if args.save else DEFAULT_SAVE_PATH
        _save_results(output_path, results)

    failures = [r for r in results if not r.raw_ok or (args.compare and r.compare_error)]
    return 1 if failures and args.validate else 0


def main() -> int:
    return run_from_args(sys.argv[1:])


if __name__ == "__main__":
    sys.exit(main())
