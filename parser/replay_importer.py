import json
import struct

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

