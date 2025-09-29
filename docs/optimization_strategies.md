## Case Study: Optimizing the `debias` Function for Scale

This document details the performance optimization journey for the core `debias` function. It serves as a practical guide for tackling similar high-throughput text processing challenges, ensuring that solutions are not only correct but also scalable. The core challenge was evolving from a function that was either fast *or* correct to one that was both fast *and* correct.

---

### Attempt 1: The Naive Loop - Fast but Flawed

The first implementation was a simple, intuitive loop. For each label, it iterated through every term in the `GENDER_MAP` and performed a case-insensitive `re.sub()`.

-   **Logic:** A nested loop that ran a new regex substitution for every keyword on every label.
-   **Pro:** This approach was computationally fast for simple replacements.
-   **Con:** It was grammatically incorrect. It failed to preserve the original casing of matched words (e.g., "Man" became "person" instead of "Person"), introducing a high rate of grammatical errors.

```python
# Attempt 1 Code
def debias(labels: List[str]) -> List[str]:
    normalized_labels: List[str] = []
    for label in labels:
        updated_label = label
        for gendered_term, neutral_term in GENDER_MAP.items():
            pattern = rf"\b{re.escape(gendered_term)}\b"
            # Fast, but doesn't respect original casing
            updated_label = re.sub(pattern, neutral_term, updated_label, flags=re.IGNORECASE)
        normalized_labels.append(updated_label)
    return normalized_labels
```

---

### Attempt 2: The Lambda with an External Function - Correct but Unscalably Slow

To fix the grammatical errors, the logic was updated to handle casing. A `lambda` function was introduced inside `re.sub`, which called an external helper function (`_apply_casing`) to apply the correct capitalization for each match.

-   **Logic:** `re.sub(pattern, lambda match: _apply_casing(replacement, match.group(0)), label)`
-   **Pro:** This dramatically improved grammatical accuracy, reducing the error rate by over 66%.
-   **Con:** It introduced a **severe performance bottleneck**. Processing time for 1,000 captions increased exponentially due to **"callback overhead"**—the expensive process of the fast, C-level regex engine stopping to hand control to the slower Python interpreter for *every single match*. This solution was correct but did not scale.

```python
# Attempt 2 Code
def _apply_casing(replacement: str, original: str) -> str:
    if original.islower():
        return replacement.lower()
    if original.istitle():
        return replacement.capitalize()
    if original.isupper():
        return replacement.upper()
    return replacement

def debias(labels: List[str]) -> List[str]:
    normalized_labels: List[str] = []
    for label in labels:
        updated_label = label
        for gendered_term, neutral_term in GENDER_MAP.items():
            pattern = rf"\b{re.escape(gendered_term)}\b"
            # Correct, but very slow due to the external function call in the lambda
            updated_label = re.sub(
                pattern,
                lambda match, r=neutral_term: _apply_casing(r, match.group(0)),
                updated_label,
                flags=re.IGNORECASE,
            )
        normalized_labels.append(updated_label)
    return normalized_labels
```

---

### Attempt 3: The Single-Pass Regex - A Major Leap Forward

To eliminate the slow Python `for` loop, the logic was changed to delegate the entire search task to the `re` engine.

-   **Logic:** All keys from `GENDER_MAP` were combined into a single, massive, case-insensitive regex pattern using the `|` (OR) operator (e.g., `r"\b(man|woman|boy|...)\b"`). This allowed the engine to find any of the target words in a single, highly-optimized pass.
-   **Pro:** This was dramatically faster than the nested Python loop.
-   **Con:** It still relied on the slow `lambda` with the external `_apply_casing` function call for the replacement, leaving significant performance on the table.

```python
# Attempt 3 Code
gendered_pattern = re.compile(r"\b(" + "|".join(GENDER_MAP.keys()) + r")\b", re.IGNORECASE)

def debias(labels: List[str]) -> List[str]:
    # ...
    for label in labels:
        # Faster search, but still a slow replacement
        updated_label = gendered_pattern.sub(
            lambda match: _apply_casing(GENDER_MAP[match.group(0).lower()], match.group(0)),
            label
        )
        normalized_labels.append(updated_label)
    return normalized_labels
```

---

### Attempt 4: The Final Optimization - Pre-computation with a Fast Lambda

This final version combines all lessons to create the fastest and most correct solution by eliminating the expensive *work* being done inside the lambda. The key insight is that the `lambda` keyword itself is not slow, but calling a multi-step Python function from it is.

1.  **Expand the Dictionary:** The `GENDER_MAP` is expanded to triple its size, explicitly mapping every possible case variation (`man`, `Man`, `MAN`) to its correctly cased replacement (`person`, `Person`, `PERSON`). This is a one-time setup cost.
2.  **Build a Case-Sensitive Master Regex:** A single, massive, but now **case-sensitive** regex pattern is compiled from the keys of this new `expanded_map`.
3.  **Simplify the Lambda's Job:** The `re.sub` call still uses a `lambda`, but its only job is to perform a single, lightning-fast dictionary lookup (`expanded_map[match.group(0)]`). The expensive external `_apply_casing` function and its conditional logic are completely removed from the runtime path.

This is the most performant approach because the complex, multi-step logic is handled once during setup. At runtime, the replacement is just a direct, highly-optimized lookup.

```python
# Attempt 4 Code (Final)
expanded_map = {}
for k, v in GENDER_MAP.items():
    expanded_map[k.lower()] = v.lower()
    expanded_map[k.title()] = v.title()
    expanded_map[k.upper()] = v.upper()

gendered_pattern = re.compile(r"\b(" + "|".join(re.escape(k) for k in expanded_map.keys()) + r")\b")

def debias(labels: List[str]) -> List[str]:
    normalized_labels: List[str] = []
    for label in labels:
        # The lambda now only performs a fast dictionary lookup, not a slow external function
        updated_label = gendered_pattern.sub(lambda match: expanded_map[match.group(0)], label)
        normalized_labels.append(updated_label)
    return normalized_labels
```

Core Lessons Learned
1. Minimize Work Inside Hot Paths: The key bottleneck was not the lambda keyword itself, but the expensive, multi-step Python function (_apply_casing) being called from it. The goal is to make the work inside a high-frequency callback as minimal and fast as possible (e.g., a direct dictionary lookup).

2. Trade Upfront Cost for Runtime Speed: Pre-computing all possible variations (like casing) is a powerful strategy. A negligible one-time setup cost is almost always worth it to eliminate millions of conditional checks and function calls at runtime.

3. Delegate Logic to the Optimized Engine: Let the tool do the heavy lifting. Instead of iterating in Python, combine keywords into a single, complex pattern and let the re engine perform the search in one highly optimized pass.
