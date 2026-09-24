"""Contact discovery policy; learning never replaces an existing contact."""

LEARN_CONTACTS = "learn_contacts"
LEARN_REPEATERS = "learn_repeaters"
LEARN_FAVORITES = "learn_favorites"
LEARN_ALLOWED = "learn_allowed"
LEARNING_KEYS = (LEARN_CONTACTS, LEARN_REPEATERS, LEARN_FAVORITES, LEARN_ALLOWED)


def learning_options(options, gateway=False):
    # Discovery, favorites and action permissions always require explicit opt-in.
    return {key: options.get(key) is True for key in LEARNING_KEYS}


def accepts_contact(contact, options):
    kind = contact.get("type")
    return (kind in (1, 3) and options[LEARN_CONTACTS]) or (kind == 2 and options[LEARN_REPEATERS])
