"""Smoke tests for the reproducible benchmark harness."""

import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_benchmark_runs_offline_without_grammar_backend(tmp_path):
    """The harness should produce a report from a checked-in caption sample."""

    captions = tmp_path / "captions.json"
    captions.write_text(
        json.dumps(
            {
                "provenance": {
                    "dataset": "test-sample",
                    "selection": "unit test",
                },
                "captions": [
                    "A man helped her.",
                    "A woman repaired the car.",
                    "Neutral text.",
                ],
            }
        ),
        encoding="utf-8",
    )
    output = tmp_path / "report.json"
    environment = dict(os.environ)
    environment["PYTHONPATH"] = str(ROOT / "src")
    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "tools" / "benchmark_coco.py"),
            "--captions-file",
            str(captions),
            "--grammar",
            "off",
            "--strategy",
            "default",
            "--sample-size",
            "3",
            "--output",
            str(output),
        ],
        capture_output=True,
        text=True,
        cwd=ROOT,
        env=environment,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    report = json.loads(output.read_text(encoding="utf-8"))
    assert report["schema"] == "nexttext.benchmark.v1"
    assert report["sample_size"] == 3
    assert report["provenance"]["dataset"] == "test-sample"
    assert report["strategies"]["default"]["changed_captions"] == 2
    assert report["strategies"]["default"]["grammar_checked"] is False


def test_benchmark_requires_existing_caption_file(tmp_path):
    """A missing caption file should be a clean usage error."""

    environment = dict(os.environ)
    environment["PYTHONPATH"] = str(ROOT / "src")
    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "tools" / "benchmark_coco.py"),
            "--captions-file",
            str(tmp_path / "missing.json"),
            "--grammar",
            "off",
        ],
        capture_output=True,
        text=True,
        cwd=ROOT,
        env=environment,
        check=False,
    )
    assert result.returncode == 2
    assert "not found" in result.stderr
