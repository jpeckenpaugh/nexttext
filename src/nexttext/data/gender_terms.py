"""Containers for gender-related term mappings."""

# --- Rules for Populating This Map ---
# 1. Base terms should be all lowercase. The processing script will automatically
#    create and handle Title Case and UPPERCASE variations.
#
# 2. The processing script automatically sorts all terms by length, from
#    longest to shortest. This means you can add complex, multi-word phrases
#    and they will be correctly prioritized over the shorter words they contain
#    without needing to order them manually in this dictionary.
#
# 3. Handle specific possessives (e.g., "man's") and contractions (e.g., "he's")
#    as explicit, individual entries for precise, controlled replacements.

GENDER_MAP: dict[str, str] = {
    # The order of entries in this dictionary does not matter.
    # Add new rules anywhere.

    # --- Base Nouns & Pronouns ---
    "man": "person",
    "woman": "person",
    "boy": "child",
    # ... etc.

    # --- Possessives & Contractions ---
    "he's": "they are",
    "she's": "they are",
    "man's": "person's",
    # ... etc.

    # --- Multi-word Phrases ---
    "a boy and a girl": "two children",
    "a girl and a boy": "two children",

    "he is": "they are",
    "she is": "they are",
    "he and she": "they",
    "she and he": "they",
    "his and her": "their",
    "her and his": "their",

    "girl": "child",
    "men": "people",
    "women": "people",
    "he": "they",
    "she": "they",
    "him": "them",
    "her": "them",
    "his": "their",
    "hers": "theirs",
    "himself": "themself",
    "herself": "themself",
}

REVERSE_GENDER_MAP: dict[str, str] = {
    "person": "man",
    "child": "boy",
    "people": "men",
    "they": "he",
    "them": "him",
    "their": "his",
    "theirs": "his",
    "themself": "himself",
}

FEMALE_REVERSE_GENDER_MAP: dict[str, str] = {
    "person": "woman",
    "child": "girl",
    "people": "women",
    "they": "she",
    "them": "her",
    "their": "her",
    "theirs": "hers",
    "themself": "herself",
}
