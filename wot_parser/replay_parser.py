import json
import struct
import argparse
import sys
from pathlib import Path

MAGIC_NUM = b"\x12\x32\x34\x11"

def parse_replay_raw(replay_path):
    blocks = []
    with open(replay_path, "rb") as replay:
        if replay.read(4) != MAGIC_NUM:
            raise ValueError(f"Not a valid WoT replay: {replay_path}")

        block_count = struct.unpack("I", replay.read(4))[0]

        for i in range(block_count):
            block_size = struct.unpack("I", replay.read(4))[0]
            block_data = replay.read(block_size)
            try:
                blocks.append(json.loads(block_data))
            except json.JSONDecodeError as e:
                raise ValueError(f"Failed to parse block {i}: {e}")

    return blocks


def main():
    parser = argparse.ArgumentParser(
        description="Extract raw JSON blocks from a World of Tanks replay file."
    )
    parser.add_argument(
        "replay",
        help="Path to the .wotreplay file"
    )
    parser.add_argument(
        "-o", "--output",
        help="Output JSON file path (default: prints to stdout)"
    )
    parser.add_argument(
        "--block",
        type=int,
        choices=[0, 1],
        help="Extract only block 0 (metadata) or block 1 (battle results). Omit for all blocks."
    )
    parser.add_argument(
        "--pretty",
        action="store_true",
        default=True,
        help="Pretty-print JSON output (default: True)"
    )
    args = parser.parse_args()

    # Validate input file
    replay_path = Path(args.replay)
    if not replay_path.exists():
        print(f"Error: file not found: {replay_path}", file=sys.stderr)
        sys.exit(1)
    if replay_path.suffix != ".wotreplay":
        print(f"Warning: file does not have .wotreplay extension", file=sys.stderr)

    # Parse
    try:
        blocks = parse_replay_raw(replay_path)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    # Select block(s)
    if args.block is not None:
        if args.block >= len(blocks):
            print(f"Error: replay only has {len(blocks)} block(s)", file=sys.stderr)
            sys.exit(1)
        output_data = blocks[args.block]
    else:
        output_data = blocks

    # Output
    indent = 2 if args.pretty else None
    json_str = json.dumps(output_data, indent=indent, ensure_ascii=False)

    if args.output:
        output_path = Path(args.output)
        output_path.write_text(json_str, encoding="utf-8")
        print(f"Saved to {output_path}")
    else:
        print(json_str)


if __name__ == "__main__":
    main()

