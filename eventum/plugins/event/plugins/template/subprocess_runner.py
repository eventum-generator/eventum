"""Subprocess runner that provides interface for running shell commands
and obtaining their results from templates.
"""

import contextlib
import os
import signal
import subprocess
import time
from dataclasses import dataclass
from io import BufferedReader
from threading import Thread
from typing import Any, cast

_READ_CHUNK_SIZE = 65536
"""Number of bytes requested from an output stream at a time."""

_KILL_WAIT_TIMEOUT = 5.0
"""Seconds to wait for a killed command to be reaped."""

_ORPHANED_READ_TIMEOUT = 5.0
"""Seconds to wait for output streams of a killed command to end."""


class SubprocessOutputLimitError(Exception):
    """Command produced more output than can be captured."""


@dataclass
class SubprocessResult:
    """Result of subprocess."""

    stdout: str
    stderr: str
    exit_code: int


class _BoundedStreamCapture:
    """Reader of a single output stream with a byte limit.

    Reads the stream in its own thread until it ends or the limit is
    exceeded. Once exceeded, reading stops, so the pipe fills up and
    the command blocks on writing until it is killed.

    Parameters
    ----------
    stream : BufferedReader
        Stream to read.

    limit : int
        Maximum number of bytes to read.

    """

    def __init__(self, stream: BufferedReader, limit: int) -> None:
        """Initialize capture and start reading the stream."""
        self._stream = stream
        self._limit = limit

        self._chunks: list[bytes] = []
        self._size = 0
        self._overflowed = False

        self._thread = Thread(
            target=self._read,
            name='subprocess-capture',
            daemon=True,
        )
        self._thread.start()

    def join(self, timeout: float) -> None:
        """Wait for reading to finish.

        Parameters
        ----------
        timeout : float
            Maximum number of seconds to wait.

        """
        self._thread.join(timeout)

    def decode(self) -> str:
        """Decode bytes captured so far.

        Returns
        -------
        str
            Captured output.

        Raises
        ------
        UnicodeDecodeError
            If captured output is not valid UTF-8.

        """
        return b''.join(self._chunks[:]).decode()

    @property
    def overflowed(self) -> bool:
        """Whether the stream exceeded the limit."""
        return self._overflowed

    @property
    def is_reading(self) -> bool:
        """Whether the stream is still being read."""
        return self._thread.is_alive()

    def _read(self) -> None:
        while True:
            try:
                chunk = self._stream.read1(_READ_CHUNK_SIZE)
            except OSError, ValueError:
                # Stream is closed while the command is being killed.
                return

            if not chunk:
                return

            self._size += len(chunk)

            if self._size > self._limit:
                self._overflowed = True
                return

            self._chunks.append(chunk)


class SubprocessRunner:
    """Runner of shell commands in subprocesses.

    Every call is bounded: the command runs under a timeout, killing it
    takes down the processes it spawned, and captured output is limited
    in size. The bounds are ceilings rather than settings - they keep a
    single template from stalling the whole application, while the
    `timeout` argument tunes an individual call below the ceiling.
    """

    DEFAULT_TIMEOUT = 30.0
    """Timeout (in seconds) applied to a call that provides none."""

    MAX_TIMEOUT = 300.0
    """Longest timeout (in seconds) a call can ask for."""

    MAX_OUTPUT_BYTES = 8 * 1024 * 1024
    """Maximum number of bytes captured from each output stream."""

    def run(
        self,
        command: str,
        cwd: str | None = None,
        env: dict[str, Any] | None = None,
        timeout: float | None = None,
    ) -> SubprocessResult:
        """Run command in a subprocess.

        Parameters
        ----------
        command : str
            Shell command to execute.

        cwd : str | None, default=None
            Working directory.

        env: dict[str, Any] | None, default=None
            Environment variables.

        timeout: float | None, default=None
            Timeout (in seconds) of command execution. Omitted and non
            positive values fall back to `DEFAULT_TIMEOUT`, values
            above `MAX_TIMEOUT` are clamped to it.

        Returns
        -------
        SubprocessResult
            Command result including its stdout, stderr and exit code.

        Raises
        ------
        subprocess.TimeoutExpired
            If command timed out.

        SubprocessOutputLimitError
            If command wrote more than `MAX_OUTPUT_BYTES` to one of its
            output streams.

        Notes
        -----
        On POSIX the command runs in its own process group, so the
        processes it spawns are killed along with it.

        """
        effective_timeout = self._resolve_timeout(timeout)

        process = subprocess.Popen(  # noqa: S602
            command,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=cwd,
            env=env,
            start_new_session=os.name == 'posix',
        )
        stdout_capture = _BoundedStreamCapture(
            stream=cast('BufferedReader', process.stdout),
            limit=self.MAX_OUTPUT_BYTES,
        )
        stderr_capture = _BoundedStreamCapture(
            stream=cast('BufferedReader', process.stderr),
            limit=self.MAX_OUTPUT_BYTES,
        )
        captures = (stdout_capture, stderr_capture)

        try:
            timed_out = self._drain(
                process=process,
                captures=captures,
                deadline=time.monotonic() + effective_timeout,
            )

            if timed_out or self._overflowed(captures):
                self._kill_process_group(process)

                for capture in captures:
                    capture.join(_ORPHANED_READ_TIMEOUT)

            stdout = stdout_capture.decode()
            stderr = stderr_capture.decode()

            # A stream can reach the limit after the command exits, so
            # the verdict is taken once reading is over.
            overflowed = self._overflowed(captures)
        finally:
            self._close_streams(process, captures)

        if timed_out:
            raise subprocess.TimeoutExpired(
                cmd=command,
                timeout=effective_timeout,
            )

        if overflowed:
            msg = 'Command produced too much output'
            raise SubprocessOutputLimitError(msg)

        return SubprocessResult(
            stdout=stdout,
            stderr=stderr,
            exit_code=cast('int', process.returncode),
        )

    def _resolve_timeout(self, timeout: float | None) -> float:
        """Resolve requested timeout into the enforced one.

        Parameters
        ----------
        timeout : float | None
            Requested timeout (in seconds).

        Returns
        -------
        float
            Timeout to enforce.

        """
        if timeout is None or timeout <= 0:
            return self.DEFAULT_TIMEOUT

        return min(timeout, self.MAX_TIMEOUT)

    @staticmethod
    def _drain(
        process: subprocess.Popen[bytes],
        captures: tuple[_BoundedStreamCapture, ...],
        deadline: float,
    ) -> bool:
        """Wait for output streams to end and the command to exit.

        Parameters
        ----------
        process : subprocess.Popen[bytes]
            Running command.

        captures : tuple[_BoundedStreamCapture, ...]
            Captures of the command output streams.

        deadline : float
            Monotonic time the command must finish by.

        Returns
        -------
        bool
            `True` if the command ran out of time, `False` if it exited
            or exceeded its output limit.

        """

        def remaining() -> float:
            return max(0.0, deadline - time.monotonic())

        for capture in captures:
            capture.join(remaining())

            if capture.overflowed:
                return False

            if capture.is_reading:
                return True

        # Streams end when the command closes them, which usually but
        # not necessarily happens at its exit.
        try:
            process.wait(timeout=remaining())
        except subprocess.TimeoutExpired:
            return True

        return False

    @staticmethod
    def _overflowed(captures: tuple[_BoundedStreamCapture, ...]) -> bool:
        """Check whether any capture exceeded its limit.

        Parameters
        ----------
        captures : tuple[_BoundedStreamCapture, ...]
            Captures of the command output streams.

        Returns
        -------
        bool
            `True` if at least one capture exceeded its limit, `False`
            otherwise.

        """
        return any(capture.overflowed for capture in captures)

    @staticmethod
    def _kill_process_group(process: subprocess.Popen[bytes]) -> None:
        """Kill the command and the processes it spawned.

        Parameters
        ----------
        process : subprocess.Popen[bytes]
            Command to kill.

        """
        if os.name == 'posix':
            try:
                os.killpg(os.getpgid(process.pid), signal.SIGKILL)
            except OSError:
                process.kill()
        else:
            process.kill()

        with contextlib.suppress(subprocess.TimeoutExpired):
            process.wait(timeout=_KILL_WAIT_TIMEOUT)

    @staticmethod
    def _close_streams(
        process: subprocess.Popen[bytes],
        captures: tuple[_BoundedStreamCapture, ...],
    ) -> None:
        """Close output streams that are no longer being read.

        A stream is left open when its reader is still blocked on it,
        which happens only when a process outside the killed group
        keeps the write end of the pipe. Closing it would block on the
        reader too, and the caller must not be held up by that.

        Parameters
        ----------
        process : subprocess.Popen[bytes]
            Command that owns the streams.

        captures : tuple[_BoundedStreamCapture, ...]
            Captures of the command output streams.

        """
        streams = (process.stdout, process.stderr)

        for stream, capture in zip(streams, captures, strict=True):
            if stream is not None and not capture.is_reading:
                stream.close()
