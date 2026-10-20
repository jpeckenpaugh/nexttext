"""End-to-end tests for the command-line interface."""

import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def run_cli(*args, stdin=None):
    """Run ``python -m nexttext`` in a subprocess."""

    environment = dict(os.environ)
    environment["PYTHONPATH"] = str(ROOT / "src")
    return subprocess.run(
        [sys.executable, "-m", "nexttext", *args],
        input=stdin,
        capture_output=True,
        text=True,
        cwd=ROOT,
        env=environment,
        check=False,
    )


def test_cli_debias_stdin():
    """Plain text should round-trip through stdin and stdout."""

    result = run_cli("debias", stdin="A man helped her.\nShe runs.\n")
    assert result.returncode == 0
    assert result.stdout == "A person helped them.\nThey runs.\n"


def test_cli_debias_file_to_file(tmp_path):
    """Input and output paths should work without stdin/stdout."""

    source = tmp_path / "input.txt"
    target = tmp_path / "output.txt"
    source.write_text("The woman smiled.\n", encoding="utf-8")
    result = run_cli("debias", str(source), "-o", str(target))
    assert result.returncode == 0
    assert target.read_text(encoding="utf-8") == "The person smiled.\n"


def test_cli_jsonl_structured():
    """JSONL mode should preserve records and add structured metadata."""

    record = {"id": 7, "caption": "A man helped her."}
    result = run_cli(
        "debias",
        "--jsonl",
        "--field",
        "caption",
        "--structured",
        stdin=json.dumps(record) + "\n",
    )
    assert result.returncode == 0
    output = json.loads(result.stdout)
    assert output["id"] == 7
    assert output["caption"] == "A person helped them."
    assert output["caption_nexttext"]["confidence"] == 0.82
    assert output["caption_nexttext"]["changed"] is True


def test_cli_inject_bias_contextual():
    """The inject-bias alias should call contextual rebiasing."""

    result = run_cli("inject-bias", "--strategy", "contextual", stdin="A person holds a baby.\n")
    assert result.returncode == 0
    assert result.stdout == "A woman holds a baby.\n"


def test_cli_flag_only():
    """The CLI should expose the flag-only safety mode."""

    result = run_cli("debias", "--flag-only", stdin="her patient\n")
    assert result.returncode == 0
    assert "[[nexttext:review" in result.stdout
    assert "their patient" not in result.stdout


def test_cli_lists_strategies():
    """The strategies subcommand should print the registry."""

    result = run_cli("strategies")
    assert result.returncode == 0
    assert {"default", "contextual", "nlp"}.issubset(result.stdout.split())


def test_cli_reports_bad_jsonl_field():
    """Missing JSONL fields should produce a usage error, not a traceback."""

    result = run_cli(
        "debias",
        "--jsonl",
        "--field",
        "caption",
        stdin='{"id": 1}\n',
    )
    assert result.returncode == 2
    assert "must be a string" in result.stderr
