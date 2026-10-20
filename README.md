# nexttext

[![CI](https://github.com/jpeckenpaugh/nexttext/actions/workflows/ci.yml/badge.svg)](https://github.com/jpeckenpaugh/nexttext/actions/workflows/ci.yml)
[![Coverage](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/jpeckenpaugh/nexttext/badges/coverage.json)](https://github.com/jpeckenpaugh/nexttext/actions/workflows/ci.yml)
[![Python](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/jpeckenpaugh/nexttext/badges/python-support.json)](https://github.com/jpeckenpaugh/nexttext/actions/workflows/ci.yml)

## Take your text to the next level.

`nexttext` is a lightweight toolkit for **neutralizing text and generating
controlled bias for testing AI pipelines**. Its default path uses regular
expressions and curated word lists rather than a language model, so behavior is
small, inspectable, deterministic, and has **zero runtime dependencies**.

It works on **input labels** (human-annotated training data) as well as
**generated labels** (outputs from captioning or classification models),
helping you prototype more consistent and testable text pipelines.

---

## ✨ Features

- 🧹 **Debias** → neutralize gendered nouns, pronouns, contractions, and
  possessives
- 🧪 **Inject bias** → `inject_bias` (and the compatible `rebias` name)
  reintroduces controlled skew for testing and validation, with optional
  context-aware strategies
- 🧭 **Strategy registry** → `default`, `contextual`, optional `nlp`, and an
  experimental `semantic` strategy behind one public API
- 🧠 **Optional NLP backend** → `nexttext[nlp]` uses spaCy POS/dependency
  information for possessive/object `her`, subject-verb agreement, and
  proper-noun exclusion
- 📚 **Documented theory and limits** → the background page explains which
  biases lexical rewriting can touch and what "neutral" cannot guarantee
- 🛡️ **Confidence and `flag_only`** → inspect structured results or annotate
  low-confidence rewrites instead of silently changing text
- 🗂️ **Configurable lexicons** → JSON/YAML overrides, locale selection, and
  neopronoun mappings
- 🔌 **Pipeline ergonomics** → CLI, JSONL, pandas accessor, and Hugging Face
  Datasets helpers
- 📊 Works on both **training data** and **model outputs**
- 🧪 Longest-phrase matching, casing preservation, and optional proper-noun
  exclusions
- 🔓 Open-source under a permissive license (MIT)

---

## 🎮 Live Demo

Try `nexttext` directly in your browser (no install required) at
**[jpeckenpaugh.github.io/nexttext](https://jpeckenpaugh.github.io/nexttext/)**.
The demo loads the Python package via [Pyodide](https://pyodide.org) and lets
you run `debias` and `inject_bias` on your own text. It is a demonstration of
the lightweight default path, not a fairness evaluation tool.

---

## 📦 Installation

`nexttext` is not yet published on PyPI. Install it from a source checkout:

```bash
pip install .
```

Optional extras:

```bash
pip install -e ".[nlp]"      # spaCy-backed nlp strategy
pip install -e ".[semantic]" # experimental embedding-assisted strategy
pip install -e ".[yaml]"     # YAML lexicon files
pip install -e ".[pandas]"   # pandas accessor
pip install -e ".[hf]"       # Hugging Face Datasets helper
pip install -e ".[benchmark]"  # COCO + LanguageTool benchmark
pip install -e ".[dev]"      # tests, lint, type checks, build
```

The `nlp` extra also needs an English model:

```bash
python -m spacy download en_core_web_sm
```

The experimental `semantic` extra needs Python 3.10 or newer because its
embedding dependency does. On Python 3.9 the strategy falls back to `nlp` (or
the lexical path), so the package itself still supports 3.9.

For development and tests:

```bash
pip install -e ".[dev]"
```

### Quality gates

Every push and pull request runs the same suite on Python 3.9 through 3.13:
`pytest` with coverage, `ruff check`, `mypy`, `python -m build`, and
`twine check`. The [`ci.yml`](.github/workflows/ci.yml) workflow is the source
of the CI and Python-support badges; the coverage badge is regenerated from the
real coverage report on each push to `main`.

---

## 🚀 Quick Start

```python
>>> from nexttext import debias, inject_bias, rebias

>>> labels = [
...   "A man seated at a table talking to a young girl.",
...   "A girl kneeling to receive communion. Her hands are folded in prayer.",
...   "A doctor speaking with his patient while a nurse takes her vitals.",
... ]

>>> for label in debias(labels):
...     print(label)
A person seated at a table talking to a young child.
A child kneeling to receive communion. Their hands are folded in prayer.
A doctor speaking with their patient while a nurse takes their vitals.

# Context-aware bias injection uses associated keywords when they are present.
>>> inject_bias(["A person working on a car with their tools."], strategy="contextual")
['A man working on a car with his tools.']

>>> inject_bias(["A person holding a baby."], strategy="contextual")
['A woman holding a baby.']

# Round trip: neutralize, then reintroduce skew.
>>> rebias(debias(["A woman holding a baby."]), strategy="contextual")
['A woman holding a baby.']

```

`inject_bias` is the explicit, test-oriented name. `rebias` is the
backward-compatible name for the same operation, so existing code keeps
working. Bias injection is for testing; see
[Misuse and safety](#️-misuse-and-safety).

### Behavior notes

```python
>>> debias(["He is here."])
['They are here.']

>>> debias(["He's here."])
['They are here.']

>>> debias(["A boy and a girl played."])
['Two children played.']

>>> debias(["her patient"])
['their patient']

>>> debias(["WoMan"])
['Person']

```

The rules are applied longest-first, so the multi-word phrase
`"a boy and a girl"` wins before `"boy"` and `"girl"` are considered. Casing is
preserved for lowercase, uppercase, and title-case matches. Mixed-case matches
such as `"WoMan"` deliberately use the capitalized replacement (`"Person"`).

In the default lexical path, `her` is treated as a possessive determiner when
it is followed by a word that can begin a noun phrase (`"her patient"` →
`"their patient"`). Otherwise it is treated as an object pronoun (`"told her"`
→ `"told them"`). This is a lexical heuristic, not part-of-speech tagging.
Select `strategy="nlp"` for dependency-aware handling.

Proper nouns are only protected when you list them explicitly. The comparison
is exact and case-sensitive:

```python
>>> debias(["Man Ray was a photographer."], proper_nouns=["Man"])
['Man Ray was a photographer.']

```

---

## 🧭 Strategies

```python
>>> from nexttext import available_strategies

>>> available_strategies()
['contextual', 'default', 'nlp', 'semantic']

```

- `default` — zero-dependency lexical maps.
- `contextual` — lexical maps plus keyword-driven feminine rebiasing.
- `nlp` — optional spaCy POS/dependency strategy. If spaCy or
  `en_core_web_sm` is unavailable, it falls back to the lexical path.
- `semantic` — experimental embedding-assisted rewrite selection. It requires
  `nexttext[semantic]`, falls back to `nlp` (or the lexical path) when the
  embedding model is unavailable, and is **not** recommended for production.
  See [`docs/decisions/advanced-backends.md`](docs/decisions/advanced-backends.md).

`debias`, `inject_bias`, and `rebias` are backward compatible: the default call
still returns a list of strings. Register your own strategy with
`nexttext.register_strategy(Strategy(...))`.

---

## 🧠 Optional NLP backend

Install the extra and model, then select the strategy:

```bash
pip install -e ".[nlp]"
python -m spacy download en_core_web_sm
```

```python
from nexttext import debias, rebias, nlp_available

if nlp_available():
    assert debias(["She runs to her house."], strategy="nlp") == [
        "They run to their house."
    ]
    assert debias(["He told her a story."], strategy="nlp") == [
        "They told them a story."
    ]
    assert debias(["Man Ray was a photographer."], strategy="nlp") == [
        "Man Ray was a photographer."
    ]
    assert rebias(["They run."], strategy="nlp") == ["He runs."]
```

The benchmark in [`docs/benchmarks/0.4.0.md`](docs/benchmarks/0.4.0.md)
compares the lexical, NLP, and experimental semantic paths on a checked-in COCO
sample and a targeted hard-case suite. The decision memo in
[`docs/decisions/advanced-backends.md`](docs/decisions/advanced-backends.md)
reports the cost, determinism, and promotion decision.

---

## 📚 Theory and scope

The theory page, [`docs/theoretical_background.md`](docs/theoretical_background.md),
explains the types of bias the library can and cannot address, why lexical
replacement is limited, what "neutral" can and cannot mean, and the ethics of
controlled stereotype injection. It cites the established work behind those
claims rather than asserting a fairness guarantee.

For a performance-focused case study of the lexical path, see
[`docs/optimization_strategies.md`](docs/optimization_strategies.md).

---

## 🛡️ Confidence, structured results, and `flag_only`

Structured results expose the output, whether it changed, the rules that fired,
per-rule confidence, and whether a rewrite was flagged:

```python
from nexttext import debias

result = debias(["her patient"], structured=True)[0]
print(result.output)
print(result.confidence)   # 0.72
print(result.rules[0].rule)  # possessive_her
```

`with_confidence=True` is the compact form:

```python
>>> debias(["The man."], with_confidence=True)
[('The person.', 0.9)]

```

`flag_only=True` keeps low-confidence text and appends an annotation instead of
rewriting it. Callers can route those rows to human review:

```python
>>> debias(["her patient"], flag_only=True)
['her patient [[nexttext:review her->their (0.72)]]']

```

High-confidence rewrites are still applied. Adjust the cutoff with
`confidence_threshold` (default `0.8`). In production, inspect
`DebiasResult.flagged` and `DebiasResult.rules` before accepting output; never
assume the neutralized text is semantically equivalent.

---

## 🗂️ Custom lexicons, locales, and neopronouns

Pass a JSON or YAML file, a mapping, a `Lexicon`, or a sequence of those.
Custom entries are merged onto the built-in English lexicon.

```json
{
  "name": "product-terms",
  "locale": "en-gb",
  "debias": {"account manager": "support lead", "manager": "lead"},
  "rebias": {"support lead": "account manager"},
  "neopronouns": {"fae": "they", "faer": "their"},
  "female_keywords": ["spacecraft"],
  "male_keywords": ["tractor"]
}
```

```python
from nexttext import debias

debias(["The account manager met a man."], lexicon="lexicon.json")
# ['The support lead met a person.']
```

Built-in neopronouns such as `xe/xem/xyr` and `ze/zir` are neutralized by
default. Regional English locales (`en-US`, `en-GB`, `en-CA`, `en-AU`) are
accepted; unsupported locales raise `ValueError` rather than silently falling
back.

---

## 🖥️ CLI and pipeline integrations

```bash
# Plain text
nexttext debias input.txt -o neutral.txt

# JSONL with structured metadata
nexttext debias --jsonl --field caption --structured captions.jsonl

# Reintroduce bias for robustness testing
nexttext inject-bias --strategy contextual neutral.txt

# List strategies
nexttext strategies
```

`python -m nexttext` works too. The CLI has no third-party dependencies and
preserves line endings in plain-text mode.

pandas:

```python
import pandas as pd
import nexttext.integrations.pandas  # registers .nexttext

frame = pd.DataFrame({"caption": ["A man helped her."]})
frame.nexttext.debias("caption")
```

Hugging Face Datasets:

```python
from datasets import Dataset
from nexttext.integrations.huggingface import debias_dataset

data = Dataset.from_dict({"caption": ["A man helped her."]})
neutral = debias_dataset(data)
```

---

## 🎯 Intended use

- Prototyping dataset cleanup and label normalization.
- Teaching or demonstrating how simple bias heuristics behave.
- Pre-processing text before an experiment or model evaluation.
- Generating deliberately biased variants of neutral text for robustness
  testing.

## 🚫 Not intended use

- Production fairness, compliance, or safety decisions.
- Legal, medical, or other high-stakes content.
- Replacing inclusive-language review or human editing.
- Claiming that the output is unbiased, objective, or semantically correct.

## ⚠️ Misuse and safety

- **No fairness guarantees.** `nexttext` rewrites surface forms. It does not
  remove stereotypes from data or models, and it does not make a system fair,
  compliant, or safe.
- **Do not use for deceptive or high-stakes content.** Do not use the library
  to generate misleading descriptions of real people or to produce medical,
  legal, financial, safety, or other consequential material without expert
  review.
- **Bias injection is for testing only.** `inject_bias` and `rebias` exist to
  create controlled variants for robustness testing, red-teaming, and
  demonstrations. Keep generated variants labeled as synthetic, separate from
  production data, and out of any workflow that presents them as facts.
- **Review before accepting output.** Inspect `DebiasResult.flagged` and
  `DebiasResult.rules`; use `flag_only` to route uncertain rewrites to a human.
  "Neutral" is a policy choice, not a proof of correctness.

---

## ⚠️ Limitations

- **Heuristic, not grammatical.** The default path does not parse sentences.
  Rules operate on words and a small set of phrases. The optional `nlp`
  strategy improves agreement but is not a full grammar checker.
- **Subject–verb agreement is lexical by default.** Rules such as
  `"He is" → "They are"` and `"He's" → "They are"` fix common pronoun cases,
  but other singular/plural rewrites may still disagree with the surrounding
  verb unless `strategy="nlp"` is installed and selected.
- **Phrase rules are deliberately conservative.** They do not cross
  coordination boundaries when doing so would duplicate or drop a referent.
  For example, `"her and his friends"` stays `"them and their friends"` rather
  than becoming `"their friends"`.
- **Word sense is not resolved.** A gendered word used as a name, title, or
  idiom is rewritten unless it is passed through `proper_nouns`; the `nlp`
  strategy can protect multi-token names such as `"Man Ray"`.
- **Possessive `her` is a heuristic in the default path.** A following adverb
  or unusual sentence structure can still be misclassified.
- **`flag_only` is a safety aid, not a guarantee.** Low-confidence rewrites
  are annotated, but high-confidence rules can still change meaning.
- **English only by default.** Built-in maps and associative keyword lists
  target English; custom lexicons can supply other mappings.
- **No runtime dependencies on the default path** means no external NLP models
  or taggers are used unless the optional extra is installed.

---

## 📊 Benchmark

The reproducible benchmark streams person-related MS-COCO captions, caches the
sample, and checks original and rewritten text with LanguageTool. It records
rewrite cost, output hashes, and optional embedding similarity. Results and
provenance are published in [`docs/benchmarks/0.4.0.md`](docs/benchmarks/0.4.0.md).

```bash
pip install -e ".[benchmark,dev,nlp,semantic]"
python -m spacy download en_core_web_sm
python tools/benchmark_coco.py \
    --captions-file tests/fixtures/coco_captions_sample.json \
    --sample-size 250 \
    --strategy default --strategy nlp --strategy semantic \
    --grammar local --similarity fastembed --warmup 5 \
    --output benchmarks/results/0.4.0.json
```

LanguageTool runs locally and requires Java. Use `--grammar public` for the
public API or `--grammar off` to measure rewrites only. The checked-in sample
at `tests/fixtures/coco_captions_sample.json` supports offline runs without
network access. The Phase 2 results and the 1,000-caption methodology remain in
[`docs/benchmarks/0.3.0.md`](docs/benchmarks/0.3.0.md).

---

## 🤝 Contributing

Contributions are welcome!
Please open an [issue](https://github.com/jpeckenpaugh/nexttext/issues) or a
[pull request](https://github.com/jpeckenpaugh/nexttext/pulls) to suggest
improvements.

---

## 📄 License

`nexttext` is open-source software released under the
[MIT License](LICENSE).
