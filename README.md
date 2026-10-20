# nexttext

[![CI](https://github.com/jpeckenpaugh/nexttext/actions/workflows/ci.yml/badge.svg)](https://github.com/jpeckenpaugh/nexttext/actions/workflows/ci.yml)
[![Coverage](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/jpeckenpaugh/nexttext/badges/coverage.json)](https://github.com/jpeckenpaugh/nexttext/actions/workflows/ci.yml)
[![Python](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/jpeckenpaugh/nexttext/badges/python-support.json)](https://github.com/jpeckenpaugh/nexttext/actions/workflows/ci.yml)

## Take your text to the next level.

`nexttext` is a lightweight, zero-runtime-dependency Python toolkit for
**neutralizing and re-framing gendered language** in text. It uses regular
expressions and curated word lists rather than a language model, so its
behavior is small, inspectable, and deterministic.

It works on **input labels** (human-annotated training data) as well as
**generated labels** (outputs from captioning or classification models),
helping you prototype more consistent and testable text pipelines.

---

## ✨ Features

- 🧹 **Debias** → neutralize gendered nouns, pronouns, contractions, and
  possessives
- 🔄 **Rebias** → reintroduce controlled skew for testing and validation, with
  optional context-aware strategies
- 📊 Works on both **training data** and **model outputs**
- ⚡ Simple API with **no runtime dependencies**
- 🧪 Longest-phrase matching, casing preservation, and optional proper-noun
  exclusions
- 🔓 Open-source under a permissive license (MIT)

---

## 🎮 Live Demo

Try `nexttext` directly in your browser (no install required) at
**[jpeckenpaugh.github.io/nexttext](https://jpeckenpaugh.github.io/nexttext/)**.
The demo loads the Python package via [Pyodide](https://pyodide.org) and lets
you run `debias` and `rebias` on your own text.

---

## 📦 Installation

`nexttext` is not yet published on PyPI. Install it from a source checkout:

```bash
pip install .
```

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
>>> from nexttext import debias, rebias

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

# Context-aware rebiasing uses associated keywords when they are present.
>>> rebias(["A person working on a car with their tools."], strategy="contextual")
['A man working on a car with his tools.']

>>> rebias(["A person holding a baby."], strategy="contextual")
['A woman holding a baby.']

# Round trip: neutralize, then reintroduce skew.
>>> rebias(debias(["A woman holding a baby."]), strategy="contextual")
['A woman holding a baby.']

```

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

`her` is treated as a possessive determiner when it is followed by a word that
can begin a noun phrase (`"her patient"` → `"their patient"`). Otherwise it is
treated as an object pronoun (`"told her"` → `"told them"`). This is a lexical
heuristic, not part-of-speech tagging.

Proper nouns are only protected when you list them explicitly. The comparison
is exact and case-sensitive:

```python
>>> debias(["Man Ray was a photographer."], proper_nouns=["Man"])
['Man Ray was a photographer.']

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

---

## ⚠️ Limitations

- **Heuristic, not grammatical.** `nexttext` does not parse sentences. Rules
  operate on words and a small set of phrases.
- **Subject–verb agreement is out of scope for this phase.** Rules such as
  `"He is" → "They are"` and `"He's" → "They are"` fix the common pronoun
  cases, but other singular/plural rewrites may still disagree with the
  surrounding verb.
- **Phrase rules are deliberately conservative.** They do not cross coordination
  boundaries when doing so would duplicate or drop a referent. For example,
  `"her and his friends"` stays `"them and their friends"` rather than becoming
  `"their friends"`.
- **Word sense is not resolved.** A gendered word used as a name, title, or
  idiom is rewritten unless it is passed through `proper_nouns`.
- **Possessive `her` is a heuristic.** A following adverb or unusual sentence
  structure can still be misclassified.
- **English only.** The maps and associative keyword lists target English.
- **No runtime dependencies** means no external NLP models or taggers are used.

---

## 📊 Benchmark

`tools/benchmark_coco.py` streams MS-COCO captions and validates the output
with LanguageTool. Install the optional benchmark dependencies and run:

```bash
pip install -e ".[benchmark]"
python tools/benchmark_coco.py
```

LanguageTool also requires Java. The script writes its outliers to
`benchmark_coco_outliers.json`.

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
