import json
import os

path = "20231008_1900_poland-Pl15_60TP_Lewandowskiego_28_desert.wotreplay"

output_filename = os.path.splitext(path)[0] + "_extracted.json"
with open(output_filename, "w", encoding="utf-8") as output_file:
    json.dump(parse_replay(path), output_file, indent=4, ensure_ascii=False)
    print(f"JSON data saved to {output_filename}")
