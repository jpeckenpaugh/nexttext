"""Reproducible COCO + LanguageTool benchmark for ``nexttext``.

The script streams person-related MS-COCO captions, caches a deterministic
sample on disk, rewrites every caption with one or more strategies, and checks
the original and rewritten text with LanguageTool.

Examples:
    # Fetch (or reuse) 1,000 captions and compare the lexical and NLP paths.
    python tools/benchmark_coco.py --sample-size 1000 \
        --strategy default --strategy nlp \
        --output benchmarks/results/0.3.0.json

    # Re-run the checked-in provenance sample without network access.
    python tools/benchmark_coco.py \
        --captions-file tests/fixtures/coco_captions_sample.json \
        --grammar local --strategy default --strategy nlp

LanguageTool runs locally and requires Java.  Pass ``--grammar public`` to use
the public LanguageTool API, or ``--grammar off`` to measure rewrites only.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import math
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

import nexttext  # noqa: E402

PERSON_KEYWORDS = [
    "man",
    "woman",
    "boy",
    "girl",
    "person",
    "men",
    "women",
    "boys",
    "girls",
    "people",
    "he",
    "she",
    "him",
    "her",
    "kid",
    "child",
]


def main(argv: Optional[Sequence[str]] = None) -> int:
    """Run the benchmark and return a process exit code."""

    args = _build_parser().parse_args(argv)
    captions, provenance = _load_captions(args)
    if args.sample_size is not None:
        captions = captions[: args.sample_size]
        provenance["evaluated_size"] = len(captions)

    strategies = args.strategy or ["default", "nlp"]
    checker, checker_info = _build_checker(args.grammar)
    similarity, similarity_info = _build_similarity(
        args.similarity, args.similarity_model
    )
    baseline = _check_all(checker, captions)
    original_vectors = (
        _embed_all(similarity, captions) if similarity is not None else None
    )

    results: Dict[str, Any] = {}
    for name in strategies:
        if args.warmup:
            nexttext.debias(captions[: args.warmup], strategy=name)
        print(f"Evaluating strategy {name!r} on {len(captions)} captions...")
        started = time.perf_counter()
        rewritten = nexttext.debias(captions, strategy=name)
        rewrite_seconds = time.perf_counter() - started
        results[name] = _score(
            captions,
            rewritten,
            baseline,
            checker,
            strategy=name,
            rewrite_seconds=rewrite_seconds,
            similarity=similarity,
            original_vectors=original_vectors,
            similarity_info=similarity_info,
        )

    report = {
        "schema": "nexttext.benchmark.v1",
        "nexttext_version": nexttext.__version__,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "provenance": provenance,
        "sample_size": len(captions),
        "grammar_backend": checker_info,
        "similarity_backend": similarity_info,
        "measurement": {
            "warmup_captions": args.warmup,
            "timing": "rewrite wall-clock after warm-up",
            "determinism": "SHA-256 of newline-joined outputs",
        },
        "strategies": results,
    }

    if checker is not None:
        checker.close()

    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        print(f"Wrote {output_path}")

    print(_summary_text(report))

    if args.report:
        report_path = Path(args.report)
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(_render_markdown(report), encoding="utf-8")
        print(f"Wrote {report_path}")
    return 0


def _build_parser() -> argparse.ArgumentParser:
    """Build the command-line parser."""

    parser = argparse.ArgumentParser(
        description="Benchmark nexttext debias on MS-COCO captions.",
    )
    parser.add_argument(
        "--sample-size",
        type=int,
        default=1000,
        help="number of person-related captions to evaluate (default: 1000)",
    )
    parser.add_argument(
        "--captions-file",
        help="checked-in JSON/JSONL caption sample; skips network access",
    )
    parser.add_argument(
        "--cache-dir",
        default=str(ROOT / "benchmarks" / "cache"),
        help="directory for the cached caption sample",
    )
    parser.add_argument(
        "--refresh",
        action="store_true",
        help="ignore the cache and stream a fresh sample",
    )
    parser.add_argument(
        "--dataset",
        default="jxie/coco_captions",
        help="Hugging Face dataset id (default: jxie/coco_captions)",
    )
    parser.add_argument(
        "--split",
        default="train",
        help="dataset split (default: train)",
    )
    parser.add_argument(
        "--strategy",
        action="append",
        help="strategy to evaluate; may be repeated (default: default and nlp)",
    )
    parser.add_argument(
        "--grammar",
        choices=["local", "public", "off"],
        default="local",
        help="LanguageTool backend (default: local)",
    )
    parser.add_argument(
        "--warmup",
        type=int,
        default=0,
        help=(
            "run each strategy on this many captions before timing "
            "(default: 0)"
        ),
    )
    parser.add_argument(
        "--similarity",
        choices=["fastembed", "off"],
        default="off",
        help="optional embedding-similarity metric (default: off)",
    )
    parser.add_argument(
        "--similarity-model",
        default="sentence-transformers/all-MiniLM-L6-v2",
        help=(
            "fastembed model used for the similarity metric "
            "(default: sentence-transformers/all-MiniLM-L6-v2)"
        ),
    )
    parser.add_argument(
        "--output",
        help="write the machine-readable JSON report to this path",
    )
    parser.add_argument(
        "--report",
        help="write a Markdown summary to this path",
    )
    return parser


def _load_captions(
    args: argparse.Namespace,
) -> Tuple[List[str], Dict[str, Any]]:
    """Load captions from a fixture, the cache, or the dataset."""

    if args.captions_file:
        captions, provenance = _read_captions_file(Path(args.captions_file))
        return captions, provenance

    cache_path = (
        Path(args.cache_dir) / f"coco_captions_{args.sample_size}.json"
    )
    if cache_path.exists() and not args.refresh:
        captions, provenance = _read_captions_file(cache_path)
        provenance["cache_path"] = str(cache_path)
        provenance["cache_hit"] = True
        return captions, provenance

    captions, provenance = _fetch_captions(
        dataset_name=args.dataset,
        split=args.split,
        sample_size=args.sample_size,
    )
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    cache_path.write_text(
        json.dumps(
            {"provenance": provenance, "captions": captions},
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    provenance["cache_path"] = str(cache_path)
    provenance["cache_hit"] = False
    return captions, provenance


def _read_captions_file(
    path: Path,
) -> Tuple[List[str], Dict[str, Any]]:
    """Read captions and provenance from a JSON or JSONL file."""

    if not path.exists():
        raise FileNotFoundError(f"caption file not found: {path}")
    text = path.read_text(encoding="utf-8")
    if path.suffix.lower() == ".jsonl":
        records = [json.loads(line) for line in text.splitlines() if line.strip()]
        provenance = {"source": str(path), "format": "jsonl"}
        captions = [
            caption
            for record in records
            for caption in [record.get("caption")]
            if isinstance(caption, str)
        ]
        return captions, provenance

    data = json.loads(text)
    if isinstance(data, list):
        captions = [
            item["caption"] if isinstance(item, dict) else str(item)
            for item in data
        ]
        return captions, {"source": str(path), "format": "json-list"}
    if not isinstance(data, dict) or not isinstance(data.get("captions"), list):
        raise ValueError(f"{path} must contain a 'captions' list or a JSON list")
    provenance = dict(data.get("provenance") or {})
    provenance.setdefault("source", str(path))
    return [str(caption) for caption in data["captions"]], provenance


def _fetch_captions(
    *,
    dataset_name: str,
    split: str,
    sample_size: int,
) -> Tuple[List[str], Dict[str, Any]]:
    """Stream person-related captions from the dataset."""

    try:
        import datasets as ds
    except ImportError as exc:
        raise ImportError(
            "fetching COCO requires the benchmark extra: "
            'pip install -e ".[benchmark]"'
        ) from exc

    print(f"Streaming {dataset_name} ({split}) for {sample_size} captions...")
    dataset = ds.load_dataset(dataset_name, split=split, streaming=True)
    captions: List[str] = []
    for example in dataset:
        caption = example.get("caption")
        if not isinstance(caption, str):
            continue
        lowered = caption.lower()
        if not any(keyword in lowered for keyword in PERSON_KEYWORDS):
            continue
        captions.append(caption)
        if len(captions) >= sample_size:
            break

    provenance = {
        "dataset": dataset_name,
        "split": split,
        "filter": "person keywords: " + ", ".join(PERSON_KEYWORDS),
        "requested_size": sample_size,
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "datasets_version": getattr(ds, "__version__", "unknown"),
        "selection": "first matching captions in streaming order",
        "reproduce": (
            f"python tools/benchmark_coco.py --sample-size {sample_size} "
            f"--dataset {dataset_name} --split {split}"
        ),
    }
    return captions, provenance


def _build_checker(
    backend: str,
) -> Tuple[Optional[Any], Dict[str, Any]]:
    """Create a LanguageTool checker and describe it."""

    if backend == "off":
        return None, {"backend": "off"}

    try:
        import language_tool_python
    except ImportError as exc:
        raise ImportError(
            "LanguageTool requires the benchmark extra: "
            'pip install -e ".[benchmark]"'
        ) from exc

    try:
        if backend == "public":
            tool = language_tool_python.LanguageToolPublicAPI("en-US")
            info = {"backend": "public-api", "language": "en-US"}
        else:
            tool = language_tool_python.LanguageTool("en-US")
            info = {
                "backend": "local",
                "language": "en-US",
                "version": getattr(tool, "version", None),
            }
    except Exception as exc:  # pragma: no cover - depends on Java/network
        raise RuntimeError(
            "LanguageTool could not start. Enable the 'local' backend with "
            "Java installed, use '--grammar public', or '--grammar off'. "
            f"Original error: {exc}"
        ) from exc
    return tool, info


def _build_similarity(
    backend: str,
    model_name: str,
) -> Tuple[Optional[Any], Dict[str, Any]]:
    """Create an optional embedding model for semantic-similarity metrics."""

    if backend == "off":
        return None, {"backend": "off"}

    try:
        from fastembed import TextEmbedding
    except ImportError as exc:
        raise ImportError(
            "embedding similarity requires the optional fastembed package: "
            "pip install fastembed"
        ) from exc

    try:
        embedder = TextEmbedding(model_name=model_name)
    except Exception as exc:  # pragma: no cover - model download/runtime
        raise RuntimeError(
            f"embedding model {model_name!r} could not be loaded: {exc}"
        ) from exc

    try:
        version = importlib.metadata.version("fastembed")
    except importlib.metadata.PackageNotFoundError:  # pragma: no cover
        version = "unknown"
    return embedder, {
        "backend": "fastembed",
        "model": model_name,
        "fastembed_version": version,
    }


def _embed_all(embedder: Any, texts: Sequence[str]) -> List[List[float]]:
    """Embed every text once so each strategy reuses the original vectors."""

    return [
        [float(value) for value in vector]
        for vector in embedder.embed(list(texts))
    ]


def _cosine(left: Sequence[float], right: Sequence[float]) -> float:
    """Return the cosine similarity of two equal-length vectors."""

    dot = sum(a * b for a, b in zip(left, right))
    left_norm = math.sqrt(sum(value * value for value in left))
    right_norm = math.sqrt(sum(value * value for value in right))
    if left_norm == 0.0 or right_norm == 0.0:
        return 0.0
    return dot / (left_norm * right_norm)


def _check_all(checker: Optional[Any], texts: Sequence[str]) -> List[int]:
    """Return the LanguageTool match count for each text."""

    if checker is None:
        return [0 for _ in texts]
    counts: List[int] = []
    for index, text in enumerate(texts, start=1):
        counts.append(len(checker.check(text)))
        if index % 100 == 0:
            print(f"  checked {index}/{len(texts)}")
    return counts


def _score(
    original: Sequence[str],
    rewritten: Sequence[str],
    baseline: Sequence[int],
    checker: Optional[Any],
    *,
    strategy: str,
    rewrite_seconds: float = 0.0,
    similarity: Optional[Any] = None,
    original_vectors: Optional[Sequence[Sequence[float]]] = None,
    similarity_info: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Compare rewritten captions with the original captions."""

    after = _check_all(checker, rewritten)
    introduced_captions = 0
    introduced_errors = 0
    resolved_errors = 0
    changed_captions = 0
    examples: List[Dict[str, Any]] = []

    for index, (source, target, before_count, after_count) in enumerate(
        zip(original, rewritten, baseline, after)
    ):
        if source != target:
            changed_captions += 1
        if after_count > before_count:
            introduced_captions += 1
            introduced_errors += after_count - before_count
            if len(examples) < 5:
                examples.append(
                    {
                        "index": index,
                        "original": source,
                        "rewritten": target,
                        "errors_before": before_count,
                        "errors_after": after_count,
                    }
                )
        elif before_count > after_count:
            resolved_errors += before_count - after_count

    size = len(original) or 1
    result = {
        "strategy": strategy,
        "changed_captions": changed_captions,
        "changed_rate": changed_captions / size,
        "baseline_captions_with_errors": sum(1 for count in baseline if count),
        "baseline_error_rate": sum(1 for count in baseline if count) / size,
        "introduced_captions": introduced_captions,
        "introduced_error_rate": introduced_captions / size,
        "introduced_errors": introduced_errors,
        "resolved_errors": resolved_errors,
        "net_error_change": introduced_errors - resolved_errors,
        "grammar_checked": checker is not None,
        "rewrite_seconds": rewrite_seconds,
        "milliseconds_per_caption": (
            rewrite_seconds * 1000.0 / size if rewrite_seconds else None
        ),
        "outputs_sha256": hashlib.sha256(
            "\n".join(rewritten).encode("utf-8")
        ).hexdigest(),
        "examples": examples,
    }

    if (
        similarity is not None
        and original_vectors is not None
        and similarity_info is not None
    ):
        rewritten_vectors = _embed_all(similarity, rewritten)
        scores = [
            _cosine(left, right)
            for left, right in zip(original_vectors, rewritten_vectors)
        ]
        result["semantic_similarity"] = {
            "backend": similarity_info.get("backend"),
            "model": similarity_info.get("model"),
            "mean": sum(scores) / len(scores) if scores else None,
            "min": min(scores) if scores else None,
            "max": max(scores) if scores else None,
        }
    else:
        result["semantic_similarity"] = None

    return result


def _summary_text(report: Dict[str, Any]) -> str:
    """Render a short human-readable summary."""

    lines = [
        f"nexttext {report['nexttext_version']} benchmark",
        f"captions: {report['sample_size']}",
        f"grammar: {report['grammar_backend']['backend']}",
        "",
        "strategy      changed   introduced   introduced-rate   net-change   ms/caption",
    ]
    for name, result in report["strategies"].items():
        milliseconds = result.get("milliseconds_per_caption")
        timing = f"{milliseconds:.1f}" if milliseconds is not None else "n/a"
        lines.append(
            f"{name:<12} {result['changed_captions']:>7} "
            f"{result['introduced_captions']:>10} "
            f"{result['introduced_error_rate']:>15.2%} "
            f"{result['net_error_change']:>11} "
            f"{timing:>11}"
        )
    return "\n".join(lines)


def _render_markdown(report: Dict[str, Any]) -> str:
    """Render a Markdown report body from a benchmark result."""

    provenance = report["provenance"]
    lines = [
        f"# nexttext {report['nexttext_version']} benchmark",
        "",
        f"Generated: `{report['generated_at']}`",
        "",
        "## Configuration",
        "",
        f"- Captions: {report['sample_size']}",
        f"- Dataset: `{provenance.get('dataset', 'checked-in sample')}`",
        f"- Split: `{provenance.get('split', 'n/a')}`",
        f"- Selection: {provenance.get('selection', 'n/a')}",
        f"- Grammar backend: `{report['grammar_backend']['backend']}`",
        f"- Warm-up captions: {report.get('measurement', {}).get('warmup_captions', 0)}",
        "",
        "## Results",
        "",
        "| Strategy | Changed | Introduced errors | Introduced rate | "
        "Resolved | Net change |",
        "| --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for name, result in report["strategies"].items():
        lines.append(
            f"| {name} | {result['changed_captions']} | "
            f"{result['introduced_captions']} | "
            f"{result['introduced_error_rate']:.2%} | "
            f"{result['resolved_errors']} | {result['net_error_change']} |"
        )
    lines.extend(
        [
            "",
            "`Introduced errors` counts captions whose rewritten form has more "
            "LanguageTool matches than the original. `Resolved` counts the "
            "opposite. Rates use the evaluated caption count as the denominator.",
            "",
            "## Cost and determinism",
            "",
            "| Strategy | Rewrite seconds | ms/caption | Output SHA-256 |",
            "| --- | ---: | ---: | --- |",
        ]
    )
    for name, result in report["strategies"].items():
        milliseconds = result.get("milliseconds_per_caption")
        timing = f"{milliseconds:.2f}" if milliseconds is not None else "n/a"
        lines.append(
            f"| {name} | {result.get('rewrite_seconds', 0.0):.2f} | "
            f"{timing} | `{result['outputs_sha256'][:16]}` |"
        )

    if report.get("similarity_backend", {}).get("backend") == "fastembed":
        model = report["similarity_backend"]["model"]
        lines.extend(
            [
                "",
                f"## Semantic similarity (`{model}`)",
                "",
                "| Strategy | Mean cosine | Min | Max |",
                "| --- | ---: | ---: | ---: |",
            ]
        )
        for name, result in report["strategies"].items():
            stats = result.get("semantic_similarity")
            if not stats:
                continue
            lines.append(
                f"| {name} | {stats['mean']:.4f} | {stats['min']:.4f} | "
                f"{stats['max']:.4f} |"
            )
        lines.extend(
            [
                "",
                "Cosine similarity is computed with a separate embedding model from "
                "the one used by the experimental selector, to reduce circularity. "
                "It is a coarse proxy for topical overlap, not a measure of meaning "
                "preservation.",
            ]
        )

    lines.append("")
    return "\n".join(lines)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (ImportError, RuntimeError, ValueError, FileNotFoundError) as error:
        print(f"benchmark error: {error}", file=sys.stderr)
        raise SystemExit(2)
