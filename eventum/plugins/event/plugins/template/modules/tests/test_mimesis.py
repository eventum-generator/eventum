import mimesis.enums as enums
import mimesis.random as random
import pytest
from mimesis import Generic

import eventum.plugins.event.plugins.template.modules.mimesis as mimesis


# ---- Test _Locale ----
def test_locale_instance():
    assert isinstance(mimesis.locale, mimesis._Locale)


def test_locale_caching():
    generator1 = mimesis.locale['en']
    generator2 = mimesis.locale['en']

    assert isinstance(generator1, Generic)
    assert generator1 is generator2  # Cached instance


def test_locale_different_instances():
    generator_en = mimesis.locale['en']
    generator_fr = mimesis.locale['fr']

    assert isinstance(generator_en, Generic)
    assert isinstance(generator_fr, Generic)
    assert generator_en is not generator_fr


def test_locale_invalid_locale():
    with pytest.raises(KeyError):
        mimesis.locale['invalid-locale']


# ---- Test enums and random import ----
def test_enums_import():
    assert mimesis.enums is enums


def test_random_import():
    assert mimesis.random is random
