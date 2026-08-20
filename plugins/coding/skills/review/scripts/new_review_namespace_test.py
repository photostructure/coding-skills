#!/usr/bin/env python3
"""Tests for new_review_namespace.py."""

from __future__ import annotations

import re
import subprocess
import sys
import unittest
from pathlib import Path
from unittest import mock

import new_review_namespace as generator


SCRIPT = Path(__file__).with_name("new_review_namespace.py")
NAMESPACE_PATTERN = re.compile(r"^[a-z]{3,6}-[a-z]{3,6}$")


class NewReviewNamespaceTest(unittest.TestCase):
    def test_colors_are_in_the_adjective_pool(self) -> None:
        self.assertLessEqual(
            set(generator.COLOR_ADJECTIVES), set(generator.ADJECTIVES)
        )

    def test_word_lists_fit_the_namespace_grammar(self) -> None:
        self.assertEqual(len(generator.ADJECTIVES), len(set(generator.ADJECTIVES)))
        self.assertEqual(len(generator.ANIMALS), len(set(generator.ANIMALS)))
        for adjective in generator.ADJECTIVES:
            self.assertRegex(adjective, r"^[a-z]{3,6}$")
        for animal in generator.ANIMALS:
            self.assertRegex(animal, r"^[a-z]{3,6}$")

    def test_chooses_an_adjective_and_animal(self) -> None:
        with mock.patch.object(
            generator.secrets, "choice", side_effect=("sly", "fox")
        ) as choice:
            self.assertEqual("sly-fox", generator.generate_namespace())

        self.assertEqual(
            [mock.call(generator.ADJECTIVES), mock.call(generator.ANIMALS)],
            choice.call_args_list,
        )

    def test_cli_prints_one_namespace(self) -> None:
        result = subprocess.run(
            [sys.executable, str(SCRIPT)],
            capture_output=True,
            check=False,
            text=True,
        )

        self.assertEqual(0, result.returncode)
        self.assertRegex(result.stdout.strip(), NAMESPACE_PATTERN)
        self.assertEqual("", result.stderr)

    def test_cli_rejects_removed_exclude_option(self) -> None:
        result = subprocess.run(
            [sys.executable, str(SCRIPT), "--exclude", "sly-fox"],
            capture_output=True,
            check=False,
            text=True,
        )

        self.assertEqual(2, result.returncode)
        self.assertIn("unrecognized arguments: --exclude sly-fox", result.stderr)


if __name__ == "__main__":
    unittest.main()
