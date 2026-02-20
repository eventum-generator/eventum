"""Tests for eventum-keyring CLI commands."""

from unittest.mock import patch

from click.testing import CliRunner

from eventum.cli.commands.eventum_keyring import cli


# --- get ---


@patch('eventum.cli.commands.eventum_keyring.get_secret')
def test_get_success(mock_get_secret):
    mock_get_secret.return_value = 'my_secret_value'
    runner = CliRunner()
    result = runner.invoke(cli, ['get', 'api_key'])
    assert result.exit_code == 0
    assert 'my_secret_value' in result.output


@patch('eventum.cli.commands.eventum_keyring.get_secret')
def test_get_not_found(mock_get_secret):
    mock_get_secret.side_effect = ValueError('Secret not found')
    runner = CliRunner()
    result = runner.invoke(cli, ['get', 'missing_key'])
    assert result.exit_code == 1


# --- set ---


@patch('eventum.cli.commands.eventum_keyring.set_secret')
def test_set_with_value(mock_set_secret):
    runner = CliRunner()
    result = runner.invoke(cli, ['set', 'api_key', 's3cret'])
    assert result.exit_code == 0
    mock_set_secret.assert_called_once_with(name='api_key', value='s3cret')


@patch('eventum.cli.commands.eventum_keyring.set_secret')
@patch('eventum.cli.commands.eventum_keyring.pwinput')
def test_set_with_prompt(mock_pwinput, mock_set_secret):
    mock_pwinput.return_value = 'prompted_value'
    runner = CliRunner()
    result = runner.invoke(cli, ['set', 'api_key'])
    assert result.exit_code == 0
    mock_set_secret.assert_called_once_with(
        name='api_key', value='prompted_value',
    )


# --- remove ---


@patch('eventum.cli.commands.eventum_keyring.remove_secret')
def test_remove_success(mock_remove_secret):
    runner = CliRunner()
    result = runner.invoke(cli, ['remove', 'api_key'])
    assert result.exit_code == 0


@patch('eventum.cli.commands.eventum_keyring.remove_secret')
def test_remove_error(mock_remove_secret):
    mock_remove_secret.side_effect = OSError('keyring error')
    runner = CliRunner()
    result = runner.invoke(cli, ['remove', 'api_key'])
    assert result.exit_code == 1
