import os
import json
from collections import defaultdict
import sys


def calculate_statistics(json_dir):
    folder_stats = defaultdict(lambda: {
        "added": 0,
        "deleted": 0,
        "count": 0,
        "found_in_files": 0,
    })
    total_files = 0 

    for filename in os.listdir(json_dir):
        if filename.endswith("_aggregated_code.json"):
            total_files += 1
            with open(os.path.join(json_dir, filename), 'r') as f:
                data = json.load(f)

                for item, metrics in data.items():
                    if isinstance(metrics, dict) and 'added' in metrics and 'deleted' in metrics:
                        folder_stats[item]["added"] += metrics["added"]
                        folder_stats[item]["deleted"] += metrics["deleted"]
                        folder_stats[item]["count"] += 1
                        folder_stats[item]["found_in_files"] += 1

    results = {}
    for item, stats in folder_stats.items():
        avg_added = stats["added"] / stats["count"] if stats["count"] > 0 else 0
        avg_deleted = stats["deleted"] / stats["count"] if stats["count"] > 0 else 0
        ratio = avg_added / avg_deleted if avg_deleted > 0 else float('inf')  
        results[item] = {
            "avg_added": avg_added,
            "avg_deleted": avg_deleted,
            "add_del_ratio": ratio,
            "found_in_files": stats["found_in_files"],
            "total_files": total_files,
        }

    sorted_results = {k: results[k] for k in sorted(results.keys())}
    return sorted_results

def main():
    if len(sys.argv) != 3:
        print("Usage: python3 vendor_code_stat.py <json directory> <output file path.json>")
        sys.exit(1)
    
    json_dir = sys.argv[1]
    output_path = sys.argv[2]
    statistics = calculate_statistics(json_dir)

    with open(output_path, "w") as outfile:
        json.dump(statistics, outfile, indent=4)

    print(f"Statistics saved to {output_path}")

if __name__ == "__main__":
    main()