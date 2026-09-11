"""Stable word identities, including migration from the former action editor."""
from uuid import NAMESPACE_URL, uuid5

from .const import CONF_ACTIONS, CONF_WORDS, DOMAIN


def validate_word(word):
    if (not isinstance(word, str) or not word.strip() or len(word.encode("utf-8")) > 130
            or any(c in word for c in ("\0", "\n", "\r"))):
        raise ValueError("A word must contain 1 to 130 UTF-8 bytes without line breaks or NUL")
    return word


def configured_words(entry):
    if CONF_WORDS in entry.options:
        return dict(entry.options[CONF_WORDS])
    return {uuid5(NAMESPACE_URL, f"{DOMAIN}/{entry.entry_id}/{word}").hex: word
            for word in entry.options.get(CONF_ACTIONS, {})}


def word_options(entry, words):
    options = dict(entry.options)
    options.pop(CONF_ACTIONS, None)
    options[CONF_WORDS] = words
    return options
