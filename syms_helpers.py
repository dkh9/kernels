import sys
import subprocess
import re

def remove_duplicates(file_path):
    """Remove duplicate lines from a file."""
    with open(file_path, "r") as f:
        lines = list(dict.fromkeys(f.readlines()))  
    with open(file_path, "w") as f:
        f.writelines(lines)

def remove_number_postfixes(file_path):
    """Sort lines by the second column, remove numeric postfixes, and remove duplicates."""
    with open(file_path, 'r') as f:
        lines = f.readlines()
    lines.sort(key=lambda x: x.split()[1] if len(x.split()) > 1 else '')

    cleaned_lines = [re.sub(r'\.[0-9]+$', '', line) for line in lines]
    with open(file_path, 'w') as f:
        f.writelines(cleaned_lines)
    remove_duplicates(file_path)

def remove_cfi_jt_postfix(file_path):
    """Remove .cfi_jt postfix from each line and remove duplicate lines."""
    with open(file_path, 'r') as f:
        lines = f.readlines()
    cleaned_lines = [re.sub(r'\.cfi_jt$', '', line) for line in lines]

    with open(file_path, 'w') as f:
        f.writelines(cleaned_lines)
    remove_duplicates(file_path)

def remove_cfi_postfix(file_path):
    """Remove .cfi postfix from each line and remove duplicate lines."""
    with open(file_path, 'r') as f:
        lines = f.readlines()
    cleaned_lines = [re.sub(r'\.cfi$', '', line) for line in lines]

    with open(file_path, 'w') as f:
        f.writelines(cleaned_lines)
    remove_duplicates(file_path)

def remove_llvm_key_msg_postfixes(file_path):
    """Remove .llvm, .__key, .__msg postfixes from each line and remove duplicate lines."""
    with open(file_path, 'r') as f:
        lines = f.readlines()

    patterns = [r'\.llvm$', r'\.__key$', r'\.__msg$']
    cleaned_lines = [
        re.sub('|'.join(patterns), '', line)
        for line in lines
    ]

    with open(file_path, 'w') as f:
        f.writelines(cleaned_lines)
    remove_duplicates(file_path)

def remove_ts(file_path):
    with open(file_path, "r") as f:
        lines = f.readlines()

    with open(file_path, "w") as f:
        for line in lines:
            if line.startswith("T "):
                f.write("t " + line[2:])
            else:
                f.write(line)
    remove_duplicates(file_path)

def remove_sym_desc(file_path):
    """Remove symbol descriptions (everything before the first space) and remove duplicate lines."""
    with open(file_path, 'r') as f:
        lines = f.readlines()

    cleaned_lines = [re.sub(r'^[^ ]* ', '', line) for line in lines]

    with open(file_path, 'w') as f:
        f.writelines(cleaned_lines)
    remove_duplicates(file_path)

def digest(file1, file2):
    output = ""
    with open(file1, "r") as f1, open(file2, "r") as f2:
        lines1 = f1.readlines()
        lines2 = f2.readlines()

    diff = abs(len(lines1) - len(lines2))
    output += f"Difference in the number of lines: {diff}\n"

    sorted_lines1 = sorted(lines1)
    sorted_lines2 = sorted(lines2)

    unique_1 = len(set(sorted_lines1) - set(sorted_lines2))
    unique_2 = len(set(sorted_lines2) - set(sorted_lines1))

    output += f"Amount of unique lines in {file1}: {unique_1}\n"
    output += f"Amount of unique lines in {file2}: {unique_2}\n"

    identical_lines_count = len(set(sorted_lines1) & set(sorted_lines2))
    output += f"Identical lines count: {identical_lines_count}\n"

    return output

def process_files(file1, file2):
    output = ""
    cycles = [
        ("Initial comparison", None),
        ("Removed number postfixes", remove_number_postfixes),
        ("Removed .cfi_jt postfixes", remove_cfi_jt_postfix),
        ("Removed number postfixes (second pass)", remove_number_postfixes),
        ("Removed .llvm, .__key, .__msg postfixes", remove_llvm_key_msg_postfixes),
        ("Resolved same symbols with both local and global T and t", remove_ts),
        ("Deleted all sym types", remove_sym_desc)
    ]

    for i, (desc, func) in enumerate(cycles):
        output += f"\nCycle {i}: {desc}\n"
        if func:
            func(file1)
            func(file2)
        output += digest(file1, file2)

    return output
