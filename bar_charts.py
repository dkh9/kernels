import json
import matplotlib.pyplot as plt
import numpy as np
import sys

def main():

    if len(sys.argv) != 3:
        print("Usage: python3 bar_charts.py <output_file_path.json> <x label>")
        sys.exit(1)

    json_file_path = sys.argv[1]
    x_label = sys.argv[2]

    with open(json_file_path, 'r') as f:
        data = json.load(f)

    keys = list(data.keys())
    avg_added = [item['avg_added'] for item in data.values()]
    avg_deleted = [item['avg_deleted'] for item in data.values()]
    found_info = [f"{item['found_in_files']}/{item['total_files']}" for item in data.values()]

    keys_with_values = [
        f"{key}\n({int(avg_added[i])}/{int(avg_deleted[i])})" for i, key in enumerate(keys)
    ]

    x = np.arange(len(keys))
    width = 0.4

    fig, ax = plt.subplots(figsize=(14, 8))

    bars_added = ax.bar(x - width/2, avg_added, width, label='Average Added', color='blue')
    bars_deleted = ax.bar(x + width/2, avg_deleted, width, label='Average Deleted', color='red')

    for i in range(len(keys)):
        pair_center = x[i]  
        pair_height = max(avg_added[i], avg_deleted[i])  
        ax.text(pair_center, pair_height + max(avg_added + avg_deleted) * 0.02,
                found_info[i], ha='center', va='bottom', fontsize=8)

    ax.set_xlabel(x_label, fontsize=12)
    ax.set_ylabel('Average Lines of Code', fontsize=12)
    ax.set_title('Average Added and Deleted Lines per Key', fontsize=16)
    ax.set_xticks(x)
    ax.set_xticklabels(keys_with_values, rotation=90, fontsize=10)
    ax.legend()

    plt.tight_layout()

    plt.show()

if __name__ == "__main__":
    main()