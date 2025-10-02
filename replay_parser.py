import json
import os
import struct

path = "20231008_1900_poland-Pl15_60TP_Lewandowskiego_28_desert.wotreplay"
magic_num = b"\x12\x32\x34\x11"
output_json = []


def replay_reader(replay_path):
    with open(replay_path, "rb") as replay:
        if replay.read(4) != magic_num:
            raise ValueError("File is not a valid World of Tanks replay")
        block_count = struct.unpack("<I", replay.read(4))[0]
        # print(block_count)

        for i in range(block_count):
            block_length = struct.unpack("<I", replay.read(4))[0]
            # print(f"BLOCK {i} length: {block_length}")
            block_data = replay.read(block_length)
            json_data = json.loads(block_data)
            output_json.append(json_data)
            # print(f"BLOCK {i} data: {json_data}")

        output_filename = os.path.splitext(path)[0] + "_extracted.json"
        with open(output_filename, "w", encoding="utf-8") as output_file:
            json.dump(output_json, output_file, indent=4, ensure_ascii=False)
        print(f"JSON data saved to {output_filename}")


replay_reader(path)
