#!/usr/bin/env python3
"""Generate a short random namespace for one code-review session."""

from __future__ import annotations

import argparse
import secrets


COLOR_ADJECTIVES = (
    "amber",
    "aqua",
    "beige",
    "black",
    "blue",
    "brown",
    "coral",
    "cyan",
    "gold",
    "gray",
    "green",
    "indigo",
    "ivory",
    "lilac",
    "lime",
    "mauve",
    "navy",
    "ochre",
    "olive",
    "orange",
    "peach",
    "pink",
    "plum",
    "purple",
    "red",
    "rose",
    "silver",
    "tan",
    "teal",
    "violet",
    "white",
    "yellow",
)

ADJECTIVES = COLOR_ADJECTIVES + (
    "apt",
    "bold",
    "brave",
    "brisk",
    "calm",
    "clear",
    "cool",
    "crisp",
    "deft",
    "eager",
    "fair",
    "fast",
    "fresh",
    "grand",
    "happy",
    "keen",
    "kind",
    "lucid",
    "merry",
    "mild",
    "neat",
    "noble",
    "proud",
    "quick",
    "quiet",
    "ready",
    "sharp",
    "shy",
    "sleek",
    "sly",
    "smart",
    "sunny",
    "swift",
    "vivid",
    "warm",
    "wise",
    "wry",
    "zesty",
)

ANIMALS = (
    "alpaca",
    "ant",
    "ape",
    "badger",
    "bear",
    "beaver",
    "bird",
    "bison",
    "boar",
    "camel",
    "coyote",
    "crane",
    "crow",
    "deer",
    "dingo",
    "dove",
    "eagle",
    "falcon",
    "ferret",
    "finch",
    "fox",
    "gecko",
    "goose",
    "gopher",
    "heron",
    "horse",
    "ibis",
    "koala",
    "lemur",
    "lion",
    "lynx",
    "marten",
    "moose",
    "mouse",
    "otter",
    "panda",
    "quail",
    "rabbit",
    "raven",
    "robin",
    "seal",
    "shark",
    "sheep",
    "sloth",
    "snail",
    "swan",
    "tiger",
    "turtle",
    "whale",
    "wolf",
    "yak",
    "zebra",
)


def generate_namespace() -> str:
    adjective = secrets.choice(ADJECTIVES)
    animal = secrets.choice(ANIMALS)
    return f"{adjective}-{animal}"


def main() -> int:
    argparse.ArgumentParser(description=__doc__).parse_args()
    print(generate_namespace())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
