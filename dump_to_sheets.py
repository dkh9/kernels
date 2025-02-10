import gspread
import os
import sys
import subprocess
import re
from datetime import datetime
from syms_helpers import process_files

root_dir = os.getenv("KERNELS_ROOT_DIR")
if not root_dir:
    raise EnvironmentError("Environment variable 'KERNELS_ROOT_DIR' is not set.")

row_values = ["FW codename",
              "Kernel version",
              "Android version",
              "Exact match", "(initial) Unique OEM/Unique GKI/Identical",
              "(numbers) Unique OEM/Unique GKI/Identical",
              "(.cfi_jt) Unique OEM/Unique GKI/Identical",
              "(numbers 2) Unique OEM/Unique GKI/Identical", "(.llvm, .__key, .__msg) Unique OEM/Unique GKI/Identical",
              "(global-local collapse) Unique OEM/Unique GKI/Identical",
              "(no sym types) Unique OEM/Unique GKI/Identical",
              ".config +/-/modif",
              "Consumer model",
              "Release date",
              "Chipset"]


def cycle_data(output):
    cycle_pattern = re.compile(r"Cycle (\d+)")
    unique_orig_pattern = re.compile(r"Amount of unique lines in orig-boot-syms\.txt:\s*(\d+)")
    unique_corresp_pattern = re.compile(r"Amount of unique lines in corresp-boot-syms\.txt:\s*(\d+)")
    identical_pattern = re.compile(r"Identical lines count:\s*(\d+)")

    cycle_data = []

    cycles = output.split("Cycle ")[1:]

    for cycle in cycles:
        cycle_match = cycle_pattern.search("Cycle " + cycle)
        if cycle_match:
            cycle_number = int(cycle_match.group(1))
        else:
            continue

        unique_orig_match = unique_orig_pattern.search(cycle)
        unique_corresp_match = unique_corresp_pattern.search(cycle)
        identical_match = identical_pattern.search(cycle)

        if unique_orig_match and unique_corresp_match and identical_match:
            unique_orig = int(unique_orig_match.group(1))
            unique_corresp = int(unique_corresp_match.group(1))
            identical = int(identical_match.group(1))

            cycle_data.append((cycle_number, unique_orig,
                              unique_corresp, identical))
    return cycle_data


def extract_image_version(target_vmlinux):
    command = f'strings {target_vmlinux} | grep -i "linux version"'
    result = subprocess.run(command, shell=True, capture_output=True, text=True)
    version_str = result.stdout

    version_match = re.search(r"Linux version (\d+\.\d+\.\d+)", version_str)
    android_version_match = re.search(r"-android(\d+)", version_str)
    build_number_match = re.search(r"\bab[0-9]+", version_str)

    kernel_version = version_match.group(1) if version_match else None
    android_version = android_version_match.group(1) if android_version_match else None
    pre_date_match = re.search(r"\w+\s+\w+\s+\d+\s+\d+:\d+:\d+\s+\w+\s+\d+", version_str)
    date_match = pre_date_match.group(0) if pre_date_match else None
    build_number = build_number_match.group(0)[2:] if build_number_match else None

    formatted_date = None
    date_obj = None
    if date_match:
        date_str_without_tz = " ".join(date_match.split()[:-2]) + " " + date_match.split()[-1]
        date_obj = datetime.strptime(date_str_without_tz, '%a %b %d %H:%M:%S %Y')
        formatted_date = date_obj.strftime('%Y-%m')

    info_dict = {"kernel version": kernel_version,
                 "android version": android_version,
                 "build number": build_number,
                 "build date": formatted_date,
                 "build date obj": date_obj}

    print(info_dict)
    return info_dict


def count_diff_lines(diff_output):
    added_lines = sum(1 for line in diff_output.splitlines() if line.startswith('+'))
    deleted_lines = sum(1 for line in diff_output.splitlines() if line.startswith('-'))
    modified_lines = sum(1 for line in diff_output.splitlines() if "->" in line)
    return [added_lines, deleted_lines, modified_lines]


def next_available_row(sheet, cols_to_sample=2):
    cols = sheet.range(1, 1, sheet.row_count, cols_to_sample)
    return max([cell.row for cell in cols if cell.value]) + 1


def fill_info(fw_image, worksheet):
    print("Fw image: ", fw_image)
    next_row = next_available_row(worksheet)
    info_row = [fw_image]
    print("Orig boot version: ")
    orig_boot_version = extract_image_version("orig-boot.elf")
    info_row.append(orig_boot_version["kernel version"])
    info_row.append(orig_boot_version["android version"])
    corresp_boot = next((file for file in ["corresp-boot.elf", "corresp-boot-oldest.elf"] if os.path.exists(file)), '')

    if corresp_boot:
        print("Corresp boot version: ")
        corresp_boot_version = extract_image_version(corresp_boot)
        info_row.append("Y" if corresp_boot_version == orig_boot_version else "N")
    else:
        print('Problem with corresponding image name! Exiting due to ', fw_image)
        return

    orig_command = f"nm -n orig-boot.elf > orig-boot-syms.txt; sed -i 's/[^ ]* //' orig-boot-syms.txt"
    corresp_command = f"nm -n {corresp_boot} > corresp-boot-syms.txt; sed -i 's/[^ ]* //' corresp-boot-syms.txt"
    subprocess.run(orig_command, shell=True, capture_output=True, text=True)
    subprocess.run(corresp_command, shell=True, capture_output=True, text=True)
    result = process_files("orig-boot-syms.txt", "corresp-boot-syms.txt")

    if result == "":
        print("Empty result digest!")
        return
    
    fin_cycle_data = cycle_data(result)
    for cycle in fin_cycle_data:
        val = f"{cycle[1]} / {cycle[2]} / {cycle[3]}"
        info_row.append(val)

    config_orig_cmd = f"{root_dir}/extract-ikconfig orig-boot.img > orig.config"
    subprocess.run(config_orig_cmd, shell=True, capture_output=True, text=True).stdout

    config_corresp_cmd = f"{root_dir}/extract-ikconfig {corresp_boot} > corresp.config"
    subprocess.run(config_corresp_cmd, shell=True, capture_output=True, text=True).stdout

    config_result = subprocess.run(f"{root_dir}/diffconfig corresp.config orig.config", shell=True, capture_output=True, text=True).stdout

    config_diff = count_diff_lines(config_result)
    config_diff_string = " / ".join(map(str, config_diff))
    info_row.append(config_diff_string)

    print("Info row: ", info_row)

    worksheet.update([info_row], f"A{next_row}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        raise ValueError("Usage: python3 dump_to_sheets.py <spreadsheet name> <vendor folder 1> <vendor folder 2>...")
    table_name = sys.argv[1]
    oem_list = sys.argv[2:]

    if len(oem_list) == 0:
        print("No vendor folder specified!")
        sys.exit()
    
    print("OEM list: ", oem_list)

    #os.chdir()?
    gc = gspread.service_account()
    sh = gc.open(table_name)

    for oem_folder in os.listdir():
        if oem_folder in oem_list and os.path.isdir(oem_folder):
            worksheet_list = sh.worksheets()
            sheet_titles = [worksheet.title for worksheet in worksheet_list]
            if oem_folder not in sheet_titles:
                worksheet = sh.add_worksheet(title=oem_folder, rows=100, cols=20)
                worksheet.update([row_values], "A1")
            worksheet = sh.worksheet(oem_folder)
            fw_images = os.listdir(oem_folder)
            oem_folder_path = os.path.join(root_dir, oem_folder)
            os.chdir(oem_folder_path)
            for image in fw_images:
                target_image_dir = os.path.join(oem_folder_path, image)
                os.chdir(target_image_dir)
                fill_info(image, worksheet)
                os.chdir(oem_folder_path)
            os.chdir(root_dir)
