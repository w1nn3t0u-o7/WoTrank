import json
import struct

magic_num = b"\x12\x32\x34\x11"


def parse_replay(replay_path):
    with open(replay_path, "rb") as replay:
        if replay.read(4) != magic_num:
            raise ValueError("File is not a valid World of Tanks replay")
        block_count = struct.unpack("<I", replay.read(4))[0]

        output_json = []
        for _ in range(block_count):
            block_length = struct.unpack("<I", replay.read(4))[0]
            block_data = replay.read(block_length)
            try:
                json_data = json.loads(block_data)
            except json.JSONDecodeError:
                json_str = block_data.decode("utf-8", errors="replace")
                json_str = json_str.replace('"racingFinishTime": Infinity,', "")
                json_data = json.loads(block_data)
            output_json.append(json_data)

    return output_json
