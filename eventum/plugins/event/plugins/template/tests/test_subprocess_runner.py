import os
import platform
import subprocess
import time
from pathlib import Path

import pytest

from eventum.plugins.event.plugins.template.subprocess_runner import (
    SubprocessOutputLimitError,
    SubprocessRunner,
)

skip_on_windows = pytest.mark.skipif(
    platform.system() == 'Windows',
    reason='POSIX shell and process groups are required',
)


class QuickTimeoutRunner(SubprocessRunner):
    DEFAULT_TIMEOUT = 0.3
    MAX_TIMEOUT = 0.3


class SmallOutputRunner(SubprocessRunner):
    MAX_OUTPUT_BYTES = 1024


def wait_pid_gone(pid: int, timeout: float = 5.0) -> bool:
    deadline = time.monotonic() + timeout

    while time.monotonic() < deadline:
        try:
            os.kill(pid, 0)
        except OSError:
            return True

        time.sleep(0.05)

    return False


def test_subprocess():
    result = SubprocessRunner().run('echo Hello, world!')

    assert result is not None

    assert result.stdout == 'Hello, world!' + os.linesep
    assert result.stderr == ''
    assert result.exit_code == 0


def test_subprocess_stderr():
    result = SubprocessRunner().run(
        command='>&2 echo error',
    )

    assert result is not None

    assert result.stdout == ''
    assert result.stderr == 'error' + os.linesep
    assert result.exit_code == 0


def test_subprocess_cwd():
    home_dir = str(Path.home())

    result = SubprocessRunner().run(command='pwd', cwd=home_dir)
    assert result is not None
    assert result.stdout == home_dir + os.linesep


def test_subprocess_env():
    if platform.system() == 'Windows':
        result = SubprocessRunner().run(
            command='echo %MY_VAR%', env={'MY_VAR': 'VALUE'}
        )
    else:
        result = SubprocessRunner().run(
            command='echo $MY_VAR', env={'MY_VAR': 'VALUE'}
        )

    assert result is not None
    assert result.stdout == 'VALUE' + os.linesep


def test_subprocess_timed_out():
    with pytest.raises(subprocess.TimeoutExpired):
        SubprocessRunner().run(
            command='sleep 10 && echo "Hello, world!"',
            timeout=0.1,
        )


@skip_on_windows
def test_subprocess_timed_out_by_default_timeout():
    with pytest.raises(subprocess.TimeoutExpired) as info:
        QuickTimeoutRunner().run(command='sleep 10')

    assert info.value.timeout == QuickTimeoutRunner.DEFAULT_TIMEOUT


@skip_on_windows
@pytest.mark.parametrize('timeout', [0, -1.0])
def test_subprocess_non_positive_timeout_falls_back_to_default(timeout):
    with pytest.raises(subprocess.TimeoutExpired) as info:
        QuickTimeoutRunner().run(command='sleep 10', timeout=timeout)

    assert info.value.timeout == QuickTimeoutRunner.DEFAULT_TIMEOUT


@skip_on_windows
def test_subprocess_requested_timeout_is_clamped_to_max():
    with pytest.raises(subprocess.TimeoutExpired) as info:
        QuickTimeoutRunner().run(command='sleep 10', timeout=60.0)

    assert info.value.timeout == QuickTimeoutRunner.MAX_TIMEOUT


@skip_on_windows
def test_subprocess_timed_out_with_closed_output_streams():
    with pytest.raises(subprocess.TimeoutExpired):
        SubprocessRunner().run(
            command='exec 1>&- 2>&-; sleep 10',
            timeout=0.3,
        )


@skip_on_windows
def test_subprocess_output_limit_exceeded():
    with pytest.raises(SubprocessOutputLimitError):
        SmallOutputRunner().run(command='head -c 4096 /dev/zero')


@skip_on_windows
def test_subprocess_output_limit_exceeded_by_endless_command():
    with pytest.raises(SubprocessOutputLimitError):
        SmallOutputRunner().run(command='yes')


@skip_on_windows
def test_subprocess_output_within_limit():
    result = SmallOutputRunner().run(command='head -c 512 /dev/zero')

    assert len(result.stdout) == 512
    assert result.exit_code == 0


@skip_on_windows
def test_subprocess_timeout_kills_spawned_processes(tmp_path: Path):
    pid_file = tmp_path / 'child.pid'

    with pytest.raises(subprocess.TimeoutExpired):
        SubprocessRunner().run(
            command=f'sleep 60 & echo $! > {pid_file}; sleep 60',
            timeout=1.0,
        )

    assert pid_file.exists()
    assert wait_pid_gone(int(pid_file.read_text()))
