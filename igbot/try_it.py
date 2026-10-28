"""Test the analyzer without Instagram:

    python -m igbot.try_it "How much is the blue hoodie?"
    python -m igbot.try_it --dm "Hi, my order hasn't arrived"
"""

import argparse
import json

from .analyzer import analyze


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("text")
    parser.add_argument("--dm", action="store_true", help="treat as a DM instead of a comment")
    args = parser.parse_args()
    result = analyze("dm" if args.dm else "comment", args.text, username="test_user")
    print(json.dumps(vars(result), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
