import json
import sys
from collections import defaultdict

def wrap_json_with_topmost_key(original_json, topmost_key):
    if not isinstance(original_json, dict):
        raise ValueError("original_json must be a dictionary")
    
    if not isinstance(topmost_key, str):
        raise ValueError("topmost_key must be a string")
    
    return {topmost_key: original_json}

def aggregate_totals(data):
    if isinstance(data, dict):
        added_total, deleted_total = 0, 0
        for key, value in data.items():
            if isinstance(value, dict) and "added" in value and "deleted" in value:
                added_total += value["added"] if value["added"] != "NONTEXT" else 0
                deleted_total += value["deleted"] if value["deleted"] != "NONTEXT" else 0
            else:
                child_added, child_deleted = aggregate_totals(value)
                added_total += child_added
                deleted_total += child_deleted

        data["added"] = added_total
        data["deleted"] = deleted_total

        return added_total, deleted_total
    return 0, 0

def parse_diff_to_json(diff_text):
    def add_to_hierarchy(path_parts, stats, current_dict):
        if len(path_parts) == 1:
            current_dict[path_parts[0]] = {
                "added": int(stats[0]) if stats[0] != "-" else "NONTEXT",
                "deleted": int(stats[1]) if stats[1] != "-" else "NONTEXT"
            }
        else:
            dir_name = path_parts[0]
            if dir_name not in current_dict:
                current_dict[dir_name] = {}
            add_to_hierarchy(path_parts[1:], stats, current_dict[dir_name])

    root = {}
    lines = diff_text.strip().split("\n")

    for line in lines:
        parts = line.split()
        path = ""
        added, deleted = parts[:2]
        if "=>" in line:
            #print(parts)
            if parts[2].startswith("{") and parts[3] == "=>":
                path = parts[2] + parts[3] + parts[4]
                #print("NEW PATH: ", path)
            else:
                 path = parts[2]
        else:
            path = parts[2]
        path_parts = []
        path_parts = path.split("/")
        add_to_hierarchy(path_parts, (added, deleted), root)

    return root

def dump_json(filename, topmost_key = None):
    diff_text = open(filename, "r").read()
    result = parse_diff_to_json(diff_text)

    if topmost_key is not None:
        result = wrap_json_with_topmost_key(result, topmost_key)

    from copy import deepcopy
    output_json = deepcopy(result)

    aggregate_totals(output_json)
    return json.dumps(output_json, indent=4)