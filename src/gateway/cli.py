"""Command line helpers: `python -m gateway.cli create-key NAME [--rpm N]` / `hash-key KEY`."""

import argparse
import sys

from .infrastructure.security.api_keys import KeyEntry, generate_key, hash_key


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m gateway.cli", description="1min-Gateway key tools"
    )
    commands = parser.add_subparsers(dest="command", required=True)

    create = commands.add_parser("create-key", help="Generate a gateway API key for an agent")
    create.add_argument("name", help="Client name (letters, digits, _ . @ -)")
    create.add_argument("--rpm", type=int, default=None, help="Requests per minute for this key")

    digest = commands.add_parser("hash-key", help="Print the SHA-256 digest of an existing key")
    digest.add_argument("key")

    args = parser.parse_args(argv)
    if args.command == "create-key":
        key = generate_key()
        entry = KeyEntry(args.name, hash_key(key), args.rpm)
        print(f"API key for '{args.name}' (shown once, give it to the agent):\n  {key}\n")
        print("Add this entry to GATEWAY_API_KEYS (comma-separated):")
        print(f"  {entry.to_config()}")
        return 0
    print(hash_key(args.key))
    return 0


if __name__ == "__main__":
    sys.exit(main())
