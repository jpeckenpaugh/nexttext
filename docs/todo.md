# nexttext v0.1.0 Development Plan

This plan outlines the 10 phases required to build, test, and release `v0.1.0` of the `nexttext` library. The focus is on creating well-organized, maintainable code for both `debias` and `rebias` functionalities.

---

### Phase 1: Project Scaffolding & Data Structures

*Goal: Establish a clean structure for managing bias-related data, separating it from the core application logic.*

-   [x] Create a new directory: `src/nexttext/data/`.
-   [x] Inside `data`, create a `__init__.py` to make it a package.
-   [x] Create a new module for gendered term definitions: `src/nexttext/data/gender_terms.py`.
-   [x] Create a new module for associative term definitions: `src/nexttext/data/associative_terms.py`.
-   [x] Add a `.gitignore` entry for `src/nexttext/data/__pycache__/` if not already covered.
-   [x] Create a new core module for the bias/rebias logic: `src/nexttext/bias.py`.
-   [x] Add a new test file for the new functionality: `tests/test_bias.py`.

---

### Phase 2: Data Population - Core Gender Terms

*Goal: Populate the data module with direct, gender-specific word mappings.*

-   [x] In `gender_terms.py`, define a `GENDER_MAP` dictionary.
-   [x] Add noun mappings (man -> person, woman -> person, boy -> child, girl -> child).
-   [x] Add plural noun mappings (men -> people, women -> people).
-   [x] Add pronoun mappings (he -> they, she -> they, him -> them, her -> them).
-   [x] Add possessive pronoun mappings (his -> their, hers -> theirs).
-   [x] Add reflexive pronoun mappings (himself -> themself, herself -> themself).
-   [x] Define a `REVERSE_GENDER_MAP` for `rebias`, mapping neutral terms to a default biased term (e.g., person -> man, child -> boy).

---

### Phase 3: Data Population - Associative Gender Terms

*Goal: Capture common gender stereotypes associated with certain keywords to enable more nuanced rebias-ing.*

-   [x] In `associative_terms.py`, define a `MALE_ASSOCIATED_KEYWORDS` set.
-   [x] Populate `MALE_ASSOCIATED_KEYWORDS` with terms like "sports", "car", "doctor", "work", "garage", "tools".
-   [x] In `associative_terms.py`, define a `FEMALE_ASSOCIATED_KEYWORDS` set.
-   [x] Populate `FEMALE_ASSOCIATED_KEYWORDS` with terms like "kitchen", "baby", "nurse", "shopping", "dress", "flowers".
-   [x] Create a function `get_dominant_gender_from_text(text)` in `associative_terms.py` that checks for the presence of these keywords and returns "male", "female", or "neutral".

---

### Phase 4: Implement the `debias` Function

*Goal: Create the core logic for neutralizing gendered language using the structured data maps.*

-   [x] In `src/nexttext/bias.py`, import the `GENDER_MAP` from `data.gender_terms`.
-   [x] Define the `debias(labels: List[str]) -> List[str]` function signature.
-   [x] Implement the iteration logic to process each string in the input list.
-   [x] For each string, iterate through the `GENDER_MAP`.
-   [x] Use a case-insensitive `re.sub()` with word boundaries (`\b`) to replace gendered terms with their neutral counterparts.
-   [x] Ensure the function handles an empty list as input without errors.
-   [x] Add comprehensive docstrings explaining what the function does, its parameters, and what it returns.

---

### Phase 5: Implement the `rebias` Function

*Goal: Create the core logic for re-introducing gendered language, laying the groundwork for contextual biasing.*

-   [x] In `src/nexttext/bias.py`, import the `REVERSE_GENDER_MAP`.
-   [x] Define the `rebias(labels: List[str]) -> List[str]` function signature.
-   [x] For this initial implementation, use the `REVERSE_GENDER_MAP` to perform a simple, default rebias (e.g., always to male terms).
-   [x] Use a case-insensitive `re.sub()` with word boundaries to replace neutral terms with their default biased counterparts.
-   [x] Ensure the function correctly handles cases where multiple neutral words appear in one sentence.
-   [x] Add comprehensive docstrings.

---

### Phase 6: Advanced `rebias` Logic - Contextual Awareness

*Goal: Enhance the `rebias` function to use the associative keywords for more "intelligent" and context-aware biasing.*

-   [ ] In `src/nexttext/bias.py`, import `get_dominant_gender_from_text` and the keyword sets.
-   [ ] Modify the `rebias` function to accept an optional `strategy` argument (e.g., `'default'`, `'contextual'`).
-   [ ] When `strategy='contextual'`, call `get_dominant_gender_from_text` on the input string first.
-   [ ] If the dominant gender is "female", use a female-specific reverse map (e.g., person -> woman). Create this map in `gender_terms.py`.
-   [ ] If the dominant gender is "male" or "neutral", fall back to the default male-biased map.
-   [ ] Update the function logic to choose the correct map before performing the `re.sub()` replacements.
-   [ ] Update the docstrings to explain the new `strategy` parameter.

---

### Phase 7: Unit Testing - `debias`

*Goal: Ensure the `debias` function is robust, reliable, and handles edge cases correctly.*

-   [ ] In `tests/test_bias.py`, add a test case for simple noun and pronoun replacement.
-   [ ] Add a test to confirm the replacement is case-insensitive (e.g., "Man", "MAN", "man" all become "person").
-   [ ] Add a test to ensure partial words are not replaced (e.g., "his" in "history" is ignored).
-   [ ] Add a test with an empty list `[]` to ensure it returns an empty list.
-   [ ] Add a test with a sentence containing no gendered words to ensure it remains unchanged.
-   [ ] Add a test with multiple gendered words in a single string.

---

### Phase 8: Unit Testing - `rebias`

*Goal: Verify that both the default and contextual `rebias` strategies work as intended.*

-   [ ] In `tests/test_bias.py`, test the default `rebias` strategy (e.g., "A person in a house" -> "A man in a house").
-   [ ] Test the contextual strategy with male-associated keywords ("A person working on a car" -> "A man working on his car").
-   [ ] Test the contextual strategy with female-associated keywords ("A person holding a baby" -> "A woman holding a baby").
-   [ ] Test the round-trip integrity: `rebias(debias(text), strategy='contextual')` should ideally return the original text if it was biased.
-   [ ] Add a test with an empty list `[]`.
-   [ ] Add a test where no neutral words are present to ensure the text is unchanged.

---

### Phase 9: API and Final Integration

*Goal: Expose the new functionality to the end-user and clean up the package's public interface.*

-   [ ] In `src/nexttext/__init__.py`, import `debias` and `rebias` from the `bias` module.
-   [ ] Add `"debias"` and `"rebias"` to the `__all__` list in `__init__.py`.
-   [ ] Remove any old, now-unused function definitions from `core.py` if they've been superseded.
-   [ ] Manually test the import: `from nexttext import debias, rebias`.
-   [ ] Review the `README.md` and update the "Quick Start" section to reflect the new, improved functions.

---

### Phase 10: Documentation & Release Preparation

*Goal: Finalize all user-facing documentation and prepare the package for a `v0.1.0` release.*

-   [ ] Ensure all new functions (`debias`, `rebias`, `get_dominant_gender_from_text`) have complete Google-style docstrings.
-   [ ] Update the main `README.md` to explain the new contextual rebias feature.
-   [ ] Check that `pyproject.toml` has the correct version number (`0.1.0`).
-   [ ] Run all tests one final time using `pytest` from the root directory to ensure everything passes.
-   [ ] Consider adding a `CHANGELOG.md` file to document the new features for `v0.1.0`.
-   [ ] Build the package (`python -m build`) and prepare for publishing.
