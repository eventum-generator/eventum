"""Mimesis module."""

import mimesis.enums as _enums
import mimesis.random as _random
from mimesis import Generic, Locale


class _Locale:
    def __init__(self) -> None:
        self._dict: dict[str, Generic] = {}

    def __getitem__(self, locale: str) -> Generic:
        if locale in self._dict:
            return self._dict[locale]

        try:
            generator = Generic(Locale(locale))
        except ValueError:
            msg = f'Unknown locale `{locale}`'
            raise KeyError(msg) from None

        self._dict[locale] = generator
        return generator


enums = _enums
random = _random

locale = _Locale()
