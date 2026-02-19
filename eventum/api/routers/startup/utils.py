"""Utils."""


def move_key_to_first_position(d: dict, key: str) -> dict:
    """Move key in dictionary to first position.

    Parameters
    ----------
    d : dict
        Dictionary.

    key : str
        Key to move.

    Returns
    -------
    dict
        Dictionary with key moved to first position or original
        dictionary.

    Notes
    -----
    If key is missing in provided dictionary then original dict is
    returned as is.

    """
    if key in d:
        return dict([(key, d.pop(key)), *d.items()])

    return d
