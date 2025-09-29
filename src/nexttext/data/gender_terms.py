"""Containers for gender-related term mappings."""

GENDER_MAP: dict[str, str] = {
    "man": "person",
    "woman": "person",
    "boy": "child",
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
