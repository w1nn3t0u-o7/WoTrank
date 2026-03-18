import json
import struct
from pathlib import Path

MAGIC_NUM = b"\x12\x32\x34\x11"


def parse_replay_blocks(replay_path: str) -> list:
    blocks = []
    with open(replay_path, "rb") as replay:
        if replay.read(4) != MAGIC_NUM:
            raise ValueError(f"Not a valid WoT replay: {replay_path}")

        block_count = struct.unpack("I", replay.read(4))[0]

        for i in range(block_count):
            size = struct.unpack("I", replay.read(4))[0]
            try:
                blocks.append(json.loads(replay.read(size)))
            except json.JSONDecodeError as e:
                raise ValueError(f"Block {i} JSON parse error: {e}")
    return blocks


def list_all_replay_maps(replay_dir: str) -> dict[str, str]:
    """Scan all replays in a directory and return {mapName: mapDisplayName}.
    Used for manually populating MAPS lookup table."""
    seen: dict[str, str] = {}
    replays = list(Path(replay_dir).rglob("*.wotreplay"))

    for path in replays:
        try:
            blocks = parse_replay_blocks(str(path))
            b0 = blocks[0]
            name = b0.get("mapName")
            display_name = b0.get("mapDisplayName")
            if name and name not in seen:
                seen[name] = display_name or ""
        except (ValueError, IndexError, KeyError):
            continue

    return dict(sorted(seen.items()))
