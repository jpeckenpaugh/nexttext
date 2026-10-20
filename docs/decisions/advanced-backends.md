# Decision memo: advanced backends for `nexttext`

- **Status:** accepted for `0.4.0`
- **Decision:** do **not** promote an embedding or LLM backend to the default
  path. Keep one embedding-assisted prototype behind an optional extra and
  mark it experimental.
- **Date:** 2026-10-20
- **Issue:** AIA-44 (Phase 3A, P3-4)
- **Evidence:** `benchmarks/results/0.4.0.json`,
  `benchmarks/results/0.4.0-hard-cases.json`,
  [`docs/benchmarks/0.4.0.md`](../benchmarks/0.4.0.md)

## 1. Question

Phase 2 shipped a zero-dependency lexical path and an optional spaCy `nlp`
strategy. Phase 3 asked whether a heavier backend — an embedding-assisted or
LLM-assisted rewriter — is worth promoting. The decision criteria were:

1. Does it reduce introduced grammar errors versus `nlp` on the Phase 2
   benchmark?
2. Does it preserve meaning at least as well?
3. What does it cost in dependencies, model size, and latency?
4. Is it deterministic and reproducible?
5. Can it remain optional without complicating the default path?

## 2. Prototype

The prototype is a new `semantic` strategy behind
`pip install "nexttext[semantic]"`:

- It starts from the grammar-aware `nlp` rewrite (or the lexical rewrite when
  spaCy is unavailable).
- It generates a bounded set of neutral synonym variants for nouns such as
  `child` → `kid`, `children` → `kids`, `people` → `individuals`.
- It embeds the original text and every candidate with
  `BAAI/bge-small-en-v1.5` through `fastembed`/ONNX on CPU.
- It selects the candidate with the highest cosine similarity to the original.

This is deliberately a small experiment. It uses a local model, requires no
external credentials, and makes no network calls after the model is cached.
The default install still has zero runtime dependencies. `semantic` is not
part of the default path and is not used by `debias` unless selected. Its
embedding dependency requires Python 3.10 or newer; on 3.9 the strategy falls
back to `nlp` (or the lexical path).

### What was not tested

An LLM rewriter was considered and rejected for this phase. Running a
credible open model on CPU would add a multi-gigabyte dependency and a much
larger evaluation surface, and no paid API credentials are available or
appropriate for this repository. The memo therefore evaluates the
embedding-assisted prototype only. Any future LLM experiment should record its
provider, credentials dependency, per-request cost, and data-retention policy
before it is run.

## 3. Method

The Phase 2 harness was extended rather than replaced:

- **Data:** the checked-in 250-caption COCO fixture used by the Phase 2
  offline run, plus the 16-caption hard-case diagnostic set.
- **Grammar metric:** LanguageTool 6.8 (`en-US`, local server). A caption is an
  introduced error when the rewrite has more LanguageTool matches than the
  original.
- **Similarity metric:** mean cosine similarity between the original and the
  rewrite using `sentence-transformers/all-MiniLM-L6-v2`, a **different**
  embedding model from the selector. This reduces the circularity of judging
  the selector with its own objective.
- **Timing:** wall-clock rewrite time after a five-caption warm-up, so lazy
  model loading is not charged to each caption.
- **Determinism:** SHA-256 of the complete rewritten output, compared across
  two independent runs.

Environment: nexttext 0.4.0, Python 3.13.5, spaCy 3.8.16 with
`en_core_web_sm` 3.8.0, fastembed 0.9.0, onnxruntime 1.31.0, LanguageTool 6.8,
Temurin 17.0.20.1+1, single CPU process.

## 4. Results

### COCO, 250 captions

| Strategy | Changed | Introduced errors | Introduced rate | Net change | ms/caption |
| --- | ---: | ---: | ---: | ---: | ---: |
| `default` | 79 | 3 | 1.20% | +3 | 0.02 |
| `nlp` | 79 | 1 | 0.40% | +1 | 1.64 |
| `semantic` | 79 | 1 | 0.40% | +1 | 4.10 |

| Strategy | Mean cosine | Min | Max |
| --- | ---: | ---: | ---: |
| `default` | 0.9709 | 0.7737 | 1.0000 |
| `nlp` | 0.9708 | 0.7737 | 1.0000 |
| `semantic` | 0.9711 | 0.7737 | 1.0000 |

### Hard cases, 16 captions

| Strategy | Introduced errors | Introduced rate | ms/caption |
| --- | ---: | ---: | ---: |
| `default` | 14 | 87.50% | 0.25 |
| `nlp` | 0 | 0.00% | 1.35 |
| `semantic` | 0 | 0.00% | 1.43 |

On the hard-case set the prototype returns the `nlp` output unchanged. Those
captions contain no `child`/`children`/`people` nouns for the selector to vary,
so it does no embedding work and its latency equals `nlp`.

### Determinism

Two independent COCO runs produced identical output hashes for all three
strategies:

| Strategy | SHA-256 (first 16) |
| --- | --- |
| `default` | `4bf4749792f2bd00` |
| `nlp` | `8af6bfa7301179a0` |
| `semantic` | `6645b8f4d4c381b9` |

The selector uses greedy maximum-similarity selection, not sampling, and ONNX
CPU inference. That is deterministic on the same model and runtime. Different
hardware, ONNX Runtime versions, or model revisions can still change the
selected candidate, so the benchmark pins the model name and records hashes.

## 5. Cost

| Item | `nlp` | `semantic` |
| --- | --- | --- |
| Runtime dependencies | `spacy` + `en_core_web_sm` | `nlp` plus `fastembed`, ONNX Runtime, tokenizers |
| Model download | spaCy model (~12 MB) | selector model (~66 MB) |
| Extra measurement model | none | `all-MiniLM-L6-v2` (~87 MB), evaluation only |
| Model load time, warm cache | 0.99 s | 0.16 s |
| Steady-state COCO latency | 1.64 ms/caption | 4.10 ms/caption |
| External API calls / fees | none | none |

The prototype costs about 2.5× the `nlp` latency on the COCO sample and adds a
tens-of-megabytes model plus the `fastembed`/ONNX dependency stack. The
similarity model is only needed to reproduce the evaluation; it is not loaded
by the strategy.

## 6. Interpretation

The prototype did **not** produce a measurable quality improvement:

- Grammar errors were identical to `nlp` on both data sets (1 vs 1 on COCO, 0
  vs 0 on hard cases). The remaining COCO error is the intentional `themself`
  rewrite that LanguageTool flags as spelling.
- Independent embedding similarity improved by 0.0003 cosine points
  (0.9708 → 0.9711), which is not a meaningful difference for this metric and
  does not establish better meaning preservation.
- The 13 changed COCO outputs are synonym substitutions (`child` → `kid`,
  `people` → `individuals`). Some are natural; others are register shifts that
  a reviewer may not want applied automatically. The selector has no notion of
  style, audience, or identity.
- The method cannot address the real limits identified in
  [`docs/theoretical_background.md`](../theoretical_background.md): word sense,
  coreference, non-binary representation, or label and pipeline bias.

The honest summary is that embedding similarity selects fluent-looking
synonyms, while the existing `nlp` path already fixes the grammar cases that
the benchmark measures. Paying 2.5× latency and a larger dependency footprint
for synonym variation is not justified.

## 7. Decision and consequences

**Do not promote.** Keep `semantic` as an opt-in, experimental strategy for
further experiments. Do not add it to the default path, do not recommend it for
production, and do not present it as a fairness improvement.

Consequences for `0.4.0`:

- `nexttext` remains zero-dependency by default.
- `default`, `contextual`, and `nlp` remain the recommended strategies.
- `semantic` is documented as experimental and falls back to `nlp` (or the
  lexical path) when `fastembed` is unavailable.
- The benchmark harness records timing, output hashes, and optional similarity
  so future backends can be compared on the same terms.
- The default path and package name are unchanged.

## 8. When to revisit

Revisit if at least one of these becomes true:

1. There is a grammar/meaning evaluation with human judgments, not only
   LanguageTool and cosine similarity.
2. An LLM rewriter shows a clear, independently measured gain on coreference,
   agreement, and meaning preservation, with a documented cost and
   data-handling policy.
3. The project needs a hosted backend and has an explicit budget and
   credentials process; that is a separate decision with security and privacy
   review.
4. A lighter model closes the latency gap and the extra dependency can be
   justified for a specific integration.

Until then, the pragmatic choice is the existing `nlp` strategy plus human
review. It is smaller, faster, deterministic, and already solves the
benchmarked failure mode.

## 9. Reproduction

```bash
pip install -e ".[benchmark,dev,nlp,semantic]"
python -m spacy download en_core_web_sm

python tools/benchmark_coco.py \
    --captions-file tests/fixtures/coco_captions_sample.json \
    --sample-size 250 \
    --strategy default --strategy nlp --strategy semantic \
    --grammar local --similarity fastembed --warmup 5 \
    --output benchmarks/results/0.4.0.json \
    --report /tmp/0.4.0-report.md

python tools/benchmark_coco.py \
    --captions-file tests/fixtures/hard_cases.json \
    --strategy default --strategy nlp --strategy semantic \
    --grammar local --similarity fastembed --warmup 5 \
    --output benchmarks/results/0.4.0-hard-cases.json
```

## 10. Limitations

- The COCO fixture is a keyword-filtered 250-caption subset, not a random
  sample of all captions.
- The hard-case set is deliberately adversarial and small.
- LanguageTool is a fluency proxy, not a bias or meaning metric.
- Cosine similarity measures topical overlap; it can reward near-copies and
  does not detect subtle meaning changes.
- Timings are from one CPU machine and are not service-level guarantees.
- The prototype only varies a small set of neutral nouns; it is not a general
  semantic rewriter.
