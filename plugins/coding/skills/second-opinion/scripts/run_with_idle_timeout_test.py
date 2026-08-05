#!/usr/bin/env python3
"""Tests for run_with_idle_timeout.py."""

from __future__ import annotations

import os
import signal
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path


SCRIPT = Path(__file__).with_name("run_with_idle_timeout.py")


def invoke(
    child_code: str,
    *,
    idle_seconds: float = 1,
    grace_seconds: float = 0.2,
    timeout: float = 4,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--idle-seconds",
            str(idle_seconds),
            "--grace-seconds",
            str(grace_seconds),
            "--",
            sys.executable,
            "-c",
            child_code,
        ],
        capture_output=True,
        check=False,
        text=True,
        timeout=timeout,
    )


def _spawn(
    child_code: str,
    *,
    idle_seconds: float,
    grace_seconds: float,
) -> subprocess.Popen[str]:
    return subprocess.Popen(
        [
            sys.executable,
            str(SCRIPT),
            "--idle-seconds",
            str(idle_seconds),
            "--grace-seconds",
            str(grace_seconds),
            "--",
            sys.executable,
            "-c",
            child_code,
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )


def is_running(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    return True


def reap(pid: int) -> None:
    if is_running(pid):
        os.kill(pid, signal.SIGKILL)


class RunWithIdleTimeoutTest(unittest.TestCase):
    def spawn(
        self,
        child_code: str,
        *,
        idle_seconds: float,
        grace_seconds: float,
    ) -> subprocess.Popen[str]:
        supervisor = _spawn(
            child_code, idle_seconds=idle_seconds, grace_seconds=grace_seconds
        )
        for pipe in (supervisor.stdout, supervisor.stderr):
            if pipe is not None:
                self.addCleanup(pipe.close)
        return supervisor

    def test_forwards_output_and_exit_status(self) -> None:
        result = invoke(
            "import sys;print('out',flush=True);"
            "print('err',file=sys.stderr,flush=True);raise SystemExit(7)"
        )

        self.assertEqual(7, result.returncode)
        self.assertEqual("out\n", result.stdout)
        self.assertEqual("err\n", result.stderr)

    def test_output_resets_idle_timer(self) -> None:
        result = invoke(
            "import time;"
            "[(print(i,flush=True),time.sleep(.15)) for i in range(4)]",
            idle_seconds=0.3,
        )

        self.assertEqual(0, result.returncode)
        self.assertEqual(["0", "1", "2", "3"], result.stdout.splitlines())

    def test_stderr_alone_resets_idle_timer(self) -> None:
        result = invoke(
            "import sys,time;"
            "[(print(i,file=sys.stderr,flush=True),time.sleep(.15)) "
            "for i in range(4)]",
            idle_seconds=0.3,
        )

        self.assertEqual(0, result.returncode)
        self.assertEqual(["0", "1", "2", "3"], result.stderr.splitlines())

    def test_silence_times_out(self) -> None:
        result = invoke(
            "import time;print('started',flush=True);time.sleep(3)",
            idle_seconds=0.2,
        )

        self.assertEqual(124, result.returncode)
        self.assertIn("idle timeout: no output for 0.2 seconds", result.stderr)

    def test_closed_streams_still_time_out(self) -> None:
        result = invoke(
            "import os,time;os.close(1);os.close(2);time.sleep(3)",
            idle_seconds=0.2,
        )

        self.assertEqual(124, result.returncode)

    # Regression ground truth was captured by running this file against the
    # staged supervisor before applying the fixes:
    # python3 plugins/coding/skills/second-opinion/scripts/run_with_idle_timeout_test.py

    def test_closed_streams_do_not_delay_completed_child(self) -> None:
        started = time.monotonic()
        result = invoke(
            "import os,time;os.close(1);os.close(2);time.sleep(.1)",
            idle_seconds=3,
        )

        self.assertEqual(0, result.returncode)
        self.assertLess(time.monotonic() - started, 1)

    def test_child_exit_124_is_not_reported_as_idle_timeout(self) -> None:
        result = invoke("raise SystemExit(124)")

        self.assertEqual(124, result.returncode)
        self.assertNotIn("idle timeout:", result.stderr)

    def test_non_finite_timeouts_are_rejected(self) -> None:
        for option in ("--idle-seconds", "--grace-seconds"):
            for value in ("nan", "inf", "-inf"):
                with self.subTest(option=option, value=value):
                    result = subprocess.run(
                        [
                            sys.executable,
                            str(SCRIPT),
                            f"{option}={value}",
                            "--",
                            sys.executable,
                            "-c",
                            "pass",
                        ],
                        capture_output=True,
                        check=False,
                        text=True,
                        timeout=2,
                    )

                    self.assertEqual(2, result.returncode)
                    self.assertIn(
                        "must be a finite number greater than zero", result.stderr
                    )

    def test_missing_command_uses_shell_status(self) -> None:
        result = subprocess.run(
            [sys.executable, str(SCRIPT), "--", "/definitely/not/a/command"],
            capture_output=True,
            check=False,
            text=True,
            timeout=2,
        )

        self.assertEqual(127, result.returncode)
        self.assertIn("command not found:", result.stderr)

    def test_prompt_file_is_passed_as_one_literal_argument(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            marker = Path(directory, "shell-expanded")
            prompt_file = Path(directory, "prompt.txt")
            prompt = (
                "don't expand $HOME or `commands` or "
                f"$(touch {marker})\nkeep the newline\n"
            )
            prompt_file.write_bytes(prompt.encode("utf-8"))
            result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--prompt-file",
                    str(prompt_file),
                    "--",
                    sys.executable,
                    "-c",
                    "import sys;print(sys.argv[1],end='')",
                    "{prompt}",
                ],
                capture_output=True,
                check=False,
                text=True,
                timeout=2,
            )

            self.assertEqual(0, result.returncode)
            self.assertEqual(prompt, result.stdout)
            self.assertFalse(marker.exists())

    def test_prompt_file_requires_exactly_one_placeholder(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            prompt_file = Path(directory, "prompt.txt")
            prompt_file.write_text("review this", encoding="utf-8")
            for command in (["missing"], ["{prompt}", "{prompt}"]):
                with self.subTest(command=command):
                    result = subprocess.run(
                        [
                            sys.executable,
                            str(SCRIPT),
                            "--prompt-file",
                            str(prompt_file),
                            "--",
                            *command,
                        ],
                        capture_output=True,
                        check=False,
                        text=True,
                        timeout=2,
                    )

                    self.assertEqual(2, result.returncode)
                    self.assertIn(
                        "command must contain exactly one {prompt} placeholder",
                        result.stderr,
                    )

    @unittest.skipUnless(os.name == "posix", "POSIX process groups")
    def test_normal_exit_kills_grandchild_that_inherits_pipes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            marker = Path(directory, "survived")
            grandchild = (
                "import pathlib,signal,time;"
                "signal.signal(signal.SIGTERM,signal.SIG_IGN);"
                "time.sleep(1);"
                f"pathlib.Path({str(marker)!r}).write_text('survived')"
            )
            result = invoke(
                "import subprocess,sys;"
                f"subprocess.Popen([sys.executable,'-c',{grandchild!r}]);"
                "print('parent done',flush=True)",
                idle_seconds=0.2,
            )
            time.sleep(1)
            self.assertEqual(0, result.returncode)
            self.assertEqual("parent done\n", result.stdout)
            self.assertFalse(marker.exists())

    @unittest.skipUnless(os.name == "posix", "POSIX process groups")
    def test_normal_exit_kills_grandchild_with_redirected_streams(self) -> None:
        supervisor = self.spawn(
            "import subprocess,sys;"
            "helper=subprocess.Popen([sys.executable,'-c','import time;time.sleep(30)'],"
            "stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL);"
            "print(helper.pid,flush=True)",
            idle_seconds=5,
            grace_seconds=0.2,
        )
        assert supervisor.stdout is not None
        helper_pid = int(supervisor.stdout.readline())
        self.addCleanup(reap, helper_pid)

        self.assertEqual(0, supervisor.wait(timeout=3))
        supervisor.stdout.close()
        self.assertFalse(is_running(helper_pid))

    @unittest.skipUnless(os.name == "posix", "POSIX process groups")
    def test_normal_exit_bounds_drain_for_escaped_grandchild(self) -> None:
        supervisor = self.spawn(
            "import os,subprocess,sys;"
            "helper=subprocess.Popen("
            "[sys.executable,'-c','import time;time.sleep(30)'],"
            "preexec_fn=os.setsid);"
            "print(helper.pid,flush=True);print('parent done',flush=True)",
            idle_seconds=1,
            grace_seconds=0.2,
        )

        def stop_supervisor() -> None:
            if supervisor.poll() is None:
                supervisor.kill()
                supervisor.wait()

        self.addCleanup(stop_supervisor)
        assert supervisor.stdout is not None
        helper_pid = int(supervisor.stdout.readline())
        self.addCleanup(reap, helper_pid)
        started = time.monotonic()

        self.assertEqual(0, supervisor.wait(timeout=2))
        elapsed = time.monotonic() - started
        self.assertEqual("parent done\n", supervisor.stdout.read())
        supervisor.stdout.close()
        self.assertLess(elapsed, 1)

    @unittest.skipUnless(os.name == "posix", "POSIX signals")
    def test_sigterm_reaps_child(self) -> None:
        supervisor = self.spawn(
            "import os,time;print(os.getpid(),flush=True);time.sleep(5)",
            idle_seconds=5,
            grace_seconds=0.2,
        )
        assert supervisor.stdout is not None
        child_pid = int(supervisor.stdout.readline())
        supervisor.send_signal(signal.SIGTERM)

        self.assertEqual(143, supervisor.wait(timeout=3))
        supervisor.stdout.close()
        self.addCleanup(reap, child_pid)
        self.assertFalse(is_running(child_pid))

    @unittest.skipUnless(os.name == "posix", "POSIX signals")
    def test_repeated_sigterm_does_not_abort_teardown(self) -> None:
        # A second signal arriving mid-teardown must not escape and leave the
        # reviewer running.
        supervisor = self.spawn(
            "import os,signal,time;"
            "signal.signal(signal.SIGTERM,signal.SIG_IGN);"
            "print(os.getpid(),flush=True);time.sleep(30)",
            idle_seconds=30,
            grace_seconds=1,
        )
        assert supervisor.stdout is not None
        child_pid = int(supervisor.stdout.readline())
        self.addCleanup(reap, child_pid)
        supervisor.send_signal(signal.SIGTERM)
        time.sleep(0.15)
        supervisor.send_signal(signal.SIGTERM)

        self.assertEqual(143, supervisor.wait(timeout=10))
        self.assertFalse(is_running(child_pid))
        supervisor.stdout.close()

    @unittest.skipUnless(os.name == "posix", "POSIX signals")
    def test_repeated_sigint_does_not_abort_teardown(self) -> None:
        supervisor = self.spawn(
            "import os,signal,time;"
            "signal.signal(signal.SIGTERM,signal.SIG_IGN);"
            "print(os.getpid(),flush=True);time.sleep(30)",
            idle_seconds=30,
            grace_seconds=1,
        )
        assert supervisor.stdout is not None
        child_pid = int(supervisor.stdout.readline())
        self.addCleanup(reap, child_pid)
        supervisor.send_signal(signal.SIGINT)
        time.sleep(0.15)
        supervisor.send_signal(signal.SIGINT)

        self.assertEqual(130, supervisor.wait(timeout=10))
        supervisor.stdout.close()
        self.assertFalse(is_running(child_pid))

    @unittest.skipUnless(
        os.name == "posix" and hasattr(signal, "SIGQUIT"), "POSIX SIGQUIT"
    )
    def test_sigquit_reaps_child(self) -> None:
        supervisor = self.spawn(
            "import os,time;print(os.getpid(),flush=True);time.sleep(30)",
            idle_seconds=30,
            grace_seconds=0.2,
        )
        assert supervisor.stdout is not None
        child_pid = int(supervisor.stdout.readline())
        self.addCleanup(reap, child_pid)
        supervisor.send_signal(signal.SIGQUIT)

        self.assertEqual(131, supervisor.wait(timeout=3))
        supervisor.stdout.close()
        self.assertFalse(is_running(child_pid))

    @unittest.skipUnless(os.name == "posix", "POSIX signals")
    def test_broken_stdout_reaps_child(self) -> None:
        # The consumer disappears while the child is quiet: forwarding its next
        # write fails, and the child must not be orphaned.
        supervisor = self.spawn(
            "import os,sys,time;print(os.getpid(),flush=True);time.sleep(.5);"
            "sys.stdout.write('progress\\n');sys.stdout.flush();time.sleep(30)",
            idle_seconds=30,
            grace_seconds=1,
        )
        assert supervisor.stdout is not None
        child_pid = int(supervisor.stdout.readline())
        self.addCleanup(reap, child_pid)
        supervisor.stdout.close()

        self.assertEqual(141, supervisor.wait(timeout=10))
        self.assertFalse(is_running(child_pid))

    @unittest.skipUnless(os.name == "posix", "POSIX signals")
    def test_signal_exit_uses_shell_status(self) -> None:
        result = invoke("import os,signal;os.kill(os.getpid(),signal.SIGTERM)")

        self.assertEqual(143, result.returncode)

    @unittest.skipUnless(os.name == "posix", "POSIX signals")
    def test_broken_stderr_reaps_child(self) -> None:
        supervisor = self.spawn(
            "import os,sys,time;print(os.getpid(),flush=True);time.sleep(.5);"
            "sys.stderr.write('progress\\n');sys.stderr.flush();time.sleep(30)",
            idle_seconds=30,
            grace_seconds=1,
        )
        assert supervisor.stdout is not None
        assert supervisor.stderr is not None
        child_pid = int(supervisor.stdout.readline())
        self.addCleanup(reap, child_pid)
        supervisor.stderr.close()

        self.assertEqual(141, supervisor.wait(timeout=10))
        self.assertFalse(is_running(child_pid))

    @unittest.skipUnless(os.name == "posix", "POSIX signals")
    def test_broken_stderr_during_timeout_uses_broken_pipe_status(self) -> None:
        supervisor = self.spawn(
            "import os,time;print(os.getpid(),flush=True);time.sleep(30)",
            idle_seconds=0.2,
            grace_seconds=0.2,
        )
        assert supervisor.stdout is not None
        assert supervisor.stderr is not None
        child_pid = int(supervisor.stdout.readline())
        self.addCleanup(reap, child_pid)
        supervisor.stderr.close()

        self.assertEqual(141, supervisor.wait(timeout=3))
        self.assertFalse(is_running(child_pid))


if __name__ == "__main__":
    unittest.main()
