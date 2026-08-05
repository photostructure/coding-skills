#!/usr/bin/env python3
"""Run a command until it exits or both output streams fall silent.

Deliberately knows nothing about what it supervises: it forwards bytes,
kills the process group after a stretch of silence, and maps the exit
status. Interpreting the child's output is the caller's job.
"""

from __future__ import annotations

import argparse
import math
import os
import queue
import signal
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import BinaryIO


IDLE_TIMEOUT_EXIT = 124
BROKEN_PIPE_EXIT = 141
PROCESS_POLL_SECONDS = 0.1
PROMPT_PLACEHOLDER = "{prompt}"

TEARDOWN_SIGNALS = tuple(
    sig
    for sig in (
        signal.SIGTERM,
        getattr(signal, "SIGHUP", None),
        signal.SIGINT,
        getattr(signal, "SIGQUIT", None),
    )
    if sig
)


def positive_seconds(value: str) -> float:
    seconds = float(value)
    if not math.isfinite(seconds) or seconds <= 0:
        raise argparse.ArgumentTypeError(
            "must be a finite number greater than zero"
        )
    return seconds


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--idle-seconds", type=positive_seconds, default=900)
    parser.add_argument("--grace-seconds", type=positive_seconds, default=30)
    parser.add_argument("--prompt-file", type=Path)
    parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    if args.command[:1] == ["--"]:
        args.command = args.command[1:]
    if not args.command:
        parser.error("a command is required after --")
    if args.prompt_file is not None:
        if args.command.count(PROMPT_PLACEHOLDER) != 1:
            parser.error(
                "command must contain exactly one {prompt} placeholder"
            )
        try:
            prompt = args.prompt_file.read_bytes().decode("utf-8")
        except (OSError, UnicodeDecodeError) as error:
            parser.error(f"cannot read UTF-8 prompt file: {error}")
        args.command = [
            prompt if argument == PROMPT_PLACEHOLDER else argument
            for argument in args.command
        ]
    return args


def read_stream(
    name: str,
    stream: BinaryIO,
    events: queue.Queue[tuple[str, bytes | None]],
) -> None:
    try:
        while chunk := stream.read(4096):
            events.put((name, chunk))
    finally:
        events.put((name, None))


def signal_tree(process: subprocess.Popen[bytes], sig: signal.Signals) -> None:
    try:
        if os.name == "posix":
            os.killpg(process.pid, sig)
        elif process.poll() is None:
            process.send_signal(sig)
    except ProcessLookupError:
        pass


def tree_is_running(process: subprocess.Popen[bytes]) -> bool:
    process.poll()
    if os.name != "posix":
        return process.returncode is None
    try:
        os.killpg(process.pid, 0)
    except ProcessLookupError:
        return False
    return True


def stop_process(process: subprocess.Popen[bytes], grace_seconds: float) -> None:
    signal_tree(process, signal.SIGTERM)
    deadline = time.monotonic() + grace_seconds
    while tree_is_running(process) and time.monotonic() < deadline:
        time.sleep(0.05)
    if tree_is_running(process):
        signal_tree(process, signal.SIGKILL)
    if process.poll() is None:
        process.wait()


def silence_output() -> None:
    """Detach broken output so interpreter shutdown can't replace our status."""
    try:
        devnull = os.open(os.devnull, os.O_WRONLY)
    except OSError:
        return
    try:
        for stream in (sys.stdout, sys.stderr):
            try:
                os.dup2(devnull, stream.fileno())
            except (OSError, ValueError):
                pass
    finally:
        os.close(devnull)


class ForwardedSignal(Exception):
    def __init__(self, signum: int) -> None:
        self.signum = signum


def run(
    command: list[str],
    idle_seconds: float,
    grace_seconds: float,
) -> int:
    process = subprocess.Popen(
        command,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        bufsize=0,
        start_new_session=os.name == "posix",
    )
    assert process.stdout is not None
    assert process.stderr is not None

    events: queue.Queue[tuple[str, bytes | None]] = queue.Queue()
    for name, stream in (("stdout", process.stdout), ("stderr", process.stderr)):
        threading.Thread(
            target=read_stream,
            args=(name, stream, events),
            daemon=True,
        ).start()

    open_streams = {"stdout", "stderr"}
    last_activity = time.monotonic()

    def forward_signal(signum: int, _frame: object) -> None:
        raise ForwardedSignal(signum)

    previous_handlers = {
        sig: signal.signal(sig, forward_signal) for sig in TEARDOWN_SIGNALS
    }

    def disarm() -> None:
        """Teardown must not be interruptible by a second signal."""
        for sig in TEARDOWN_SIGNALS:
            signal.signal(sig, signal.SIG_IGN)

    returncode: int | None = None
    drain_deadline: float | None = None
    try:
        try:
            while open_streams or returncode is None:
                if returncode is None:
                    returncode = process.poll()
                    if returncode is not None:
                        # A successful reviewer must not leave same-group tools
                        # behind, even when they close or inherit its pipes.
                        stop_process(process, grace_seconds)
                        # A process outside that group can still inherit a pipe.
                        # Never let it turn a completed review into a hang.
                        drain_deadline = time.monotonic() + grace_seconds

                if returncode is not None:
                    if not open_streams:
                        break
                    assert drain_deadline is not None
                    drain_remaining = drain_deadline - time.monotonic()
                    if drain_remaining <= 0:
                        break
                    try:
                        name, chunk = events.get(timeout=drain_remaining)
                    except queue.Empty:
                        break
                else:
                    remaining = idle_seconds - (
                        time.monotonic() - last_activity
                    )
                    if remaining <= 0:
                        disarm()
                        stop_process(process, grace_seconds)
                        print(
                            "\nidle timeout: no output for "
                            f"{idle_seconds:g} seconds",
                            file=sys.stderr,
                            flush=True,
                        )
                        return IDLE_TIMEOUT_EXIT

                    try:
                        name, chunk = events.get(
                            timeout=min(remaining, PROCESS_POLL_SECONDS)
                        )
                    except queue.Empty:
                        continue

                if chunk is None:
                    open_streams.discard(name)
                    continue

                last_activity = time.monotonic()
                target = sys.stderr if name == "stderr" else sys.stdout
                target.buffer.write(chunk)
                target.buffer.flush()
        except BaseException:
            # Every abnormal exit reaps the tree; a leaked reviewer is the
            # exact failure this supervisor exists to prevent.
            disarm()
            stop_process(process, grace_seconds)
            raise
    except ForwardedSignal as forwarded:
        return 128 + forwarded.signum
    except KeyboardInterrupt:
        return 130
    except BrokenPipeError:
        silence_output()
        return BROKEN_PIPE_EXIT
    finally:
        for sig, previous in previous_handlers.items():
            signal.signal(sig, previous)

    assert returncode is not None
    return 128 - returncode if returncode < 0 else returncode


def main() -> int:
    args = parse_args()
    try:
        return run(args.command, args.idle_seconds, args.grace_seconds)
    except FileNotFoundError as error:
        print(f"command not found: {error.filename}", file=sys.stderr)
        return 127


if __name__ == "__main__":
    raise SystemExit(main())
