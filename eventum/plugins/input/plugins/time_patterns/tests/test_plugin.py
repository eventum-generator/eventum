import os
from pathlib import Path

import pytest
from zoneinfo import ZoneInfo

from eventum.plugins.exceptions import PluginConfigurationError
from eventum.plugins.input.plugins.time_patterns.config import (
    TimePatternsInputPluginConfig,
)
from eventum.plugins.input.plugins.time_patterns.plugin import (
    TimePatternsInputPlugin,
)

STATIC_FILES_DIR = Path(__file__).parent / 'static'


def test_plugin():
    config = TimePatternsInputPluginConfig(
        patterns=[
            STATIC_FILES_DIR / 'pattern1.yml',
            STATIC_FILES_DIR / 'pattern2.yml',
            STATIC_FILES_DIR / 'pattern3.yml',
        ]
    )
    plugin = TimePatternsInputPlugin(
        config=config, params={'id': 1, 'timezone': ZoneInfo('UTC')}
    )

    timestamps = []
    for batch in plugin.generate(1000, skip_past=False):
        timestamps.extend(batch)

    assert timestamps

    # Expected distribution:
    # ===================================================================== #
    #                                           .-.            .            #
    #                                           +#+           -=-           #
    #                                          .##*.          *#*+..        #
    #          ..            .            -+. .=###+         -####*+        #
    #         .*=           .=-          .*#*+*####*-  +=.  .*#####* -.     #
    #    ..   =##-          -##=. .=+.   +###########==##+.-*######*+#+     #
    #   -*+..=###*.  .-.   .*###*+*##-  .*################*###########*.    #
    #   =##**#####=..+#+   +#########=  .*#############################+    #
    #  -###########**###+-=###########- .##############################*.   #
    # .*###############################--###############################*-. #
    # ===================================================================== #

    # Uncomment section below to visualize distribution

    # import plotly.graph_objects as go  # type: ignore[import-untyped]

    # go.Figure(data=[go.Histogram(x=timestamps, nbinsx=300)]).show()


def test_time_pattern_invalid_config():
    config = TimePatternsInputPluginConfig(
        patterns=[
            STATIC_FILES_DIR / 'invalid.yml',
        ]
    )

    with pytest.raises(PluginConfigurationError):
        TimePatternsInputPlugin(
            config=config, params={'id': 1, 'timezone': ZoneInfo('UTC')}
        )


def test_time_pattern_dotted_keys_config():
    params = {'id': 1, 'timezone': ZoneInfo('UTC')}

    dotted_plugin = TimePatternsInputPlugin(
        config=TimePatternsInputPluginConfig(
            patterns=[STATIC_FILES_DIR / 'pattern_dotted.yml'],
        ),
        params=params,
    )
    canonical_plugin = TimePatternsInputPlugin(
        config=TimePatternsInputPluginConfig(
            patterns=[STATIC_FILES_DIR / 'pattern1.yml'],
        ),
        params=params,
    )

    dotted_config = dotted_plugin._time_patterns[0].config
    canonical_config = canonical_plugin._time_patterns[0].config
    assert dotted_config == canonical_config


def test_time_pattern_conflicting_dotted_keys_config():
    config = TimePatternsInputPluginConfig(
        patterns=[
            STATIC_FILES_DIR / 'pattern_conflicting.yml',
        ]
    )

    with pytest.raises(PluginConfigurationError) as exc:
        TimePatternsInputPlugin(
            config=config, params={'id': 1, 'timezone': ZoneInfo('UTC')}
        )

    assert 'oscillator.start' in exc.value.context['reason']
