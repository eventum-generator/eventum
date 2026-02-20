"""Splash screen for printing it on app startup."""

import platform

import click

import eventum

APP_VERSION = eventum.__version__
PYTHON_VERSION = platform.python_version()

APP_BANNER = click.style(
    text=r"""
 ________                                __
/        |                              /  |
$$$$$$$$/__     __  ______   _______   _$$ |_    __    __  _____  ____
$$ |__  /  \   /  |/      \ /       \ / $$   |  /  |  /  |/     \/    \
$$    | $$  \ /$$//$$$$$$  |$$$$$$$  |$$$$$$/   $$ |  $$ |$$$$$$ $$$$  |
$$$$$/   $$  /$$/ $$    $$ |$$ |  $$ |  $$ | __ $$ |  $$ |$$ | $$ | $$ |
$$ |_____ $$ $$/  $$$$$$$$/ $$ |  $$ |  $$ |/  |$$ \__$$ |$$ | $$ | $$ |
$$       | $$$/   $$       |$$ |  $$ |  $$  $$/ $$    $$/ $$ | $$ | $$ |
$$$$$$$$/   $/     $$$$$$$/ $$/   $$/    $$$$/   $$$$$$/  $$/  $$/  $$/""",
    fg=(130, 130, 239),
)

APP_DESCRIPTION = click.style(
    text="""
=========================================================================
                  Eventum - Data generation platform
=========================================================================
""",
    fg=(130, 130, 239),
    bold=True,
)

APP_VERSION_INFO = f"""\
App version: {click.style(APP_VERSION, fg='cyan')}
Python version: {click.style(PYTHON_VERSION, fg='cyan')}
Platform: {click.style(platform.platform(), fg='green')}
"""

SPLASH_SCREEN = APP_BANNER + APP_DESCRIPTION + APP_VERSION_INFO
