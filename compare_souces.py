import os
import sys
import subprocess
import shutil

TEST_COMMAND="git checkout -b "
EXISTING_BRANCH_COMMAND = "git checkout -f "
COMPARE_SOURCES_DIR="/home/dasha/k-pop/codebase-comparison" #set your path
COPY_COMMAND = "cp -r "

def clear_directory(dir_path):
    if not os.path.exists(dir_path) or not os.path.isdir(dir_path):
        raise ValueError(f"Invalid directory path: {dir_path}")
    
    for item in os.listdir(dir_path):
        if item.startswith("."):
            continue
        item_path = os.path.join(dir_path, item)
        if os.path.isfile(item_path) or os.path.islink(item_path):
            os.unlink(item_path)  
        elif os.path.isdir(item_path):
            shutil.rmtree(item_path)  

def checkout_branch(branch_name, source_path):
    """
    Checks out a git branch. If it exists, switches to it.
    Otherwise, creates a new branch and copies source files into it.
    """
    os.chdir(COMPARE_SOURCES_DIR)
    result = subprocess.run(TEST_COMMAND + branch_name, shell=True, capture_output=True, text=True)

    if "already exists" in result.stderr:
        print(f"Branch {branch_name} already exists!")
        subprocess.run(EXISTING_BRANCH_COMMAND + branch_name, shell=True, capture_output=True, text=True)
    elif "Switched to a new branch" in result.stderr:
        print(f"Branch {branch_name} did not exist, creating it.")
        clear_directory(COMPARE_SOURCES_DIR)
        print("Cleared directory")
        copy_command = f'{COPY_COMMAND} {source_path}/* . ; git add . ; git commit -m "Add codebase from {branch_name}"'
        subprocess.run(copy_command, shell=True, capture_output=True, text=True)
    else:
        print(f"Unexpected error while checking out {branch_name}")
        sys.exit(1)


def main():
    if len(sys.argv) != 4:
        print("Usage: compare_sources.py <gki_branch_name> <vendor_branch_name> <output folder path>")
        sys.exit(1)
    
    gki_branch_name = sys.argv[1]
    vendor_branch_name = sys.argv[2]
    output_folder_path = sys.argv[3]

    gki_path = os.getenv("GKI")
    vendor_path = os.getenv("VENDOR")

    if gki_path is None or vendor_path is None:
        print("Error: Environment variables GKI and VENDOR must be set.")
        sys.exit(1)
    
    print(f"GKI Branch Name: {gki_branch_name}")
    print(f"Vendor Branch Name: {vendor_branch_name}")
    print(f"GKI Path: {gki_path}")
    print(f"Vendor Path: {vendor_path}")

    checkout_branch(f"gki_{gki_branch_name}", gki_path)
    checkout_branch(f"vendor_{vendor_branch_name}", vendor_path)

    DIFF_CMD = "git diff {} {} --numstat > ../{}/{}.txt".format("gki_"+gki_branch_name, "vendor_"+vendor_branch_name, output_folder_path, vendor_branch_name)
    result = subprocess.run(DIFF_CMD, shell=True, capture_output=True, text=True)
 
    ONLY_CODE_DIFF = (
    f"git diff gki_{gki_branch_name} vendor_{vendor_branch_name} --numstat "
    "'***.a51' '***.asm' '***.nasm' '***.S' '***.s' '***.c' '***.cats' '***.ec' "
    "'***.idc' '***.pgc' '***.C' '***.c' '***.c++m' '***.cc' '***.ccm' '***.CPP' "
    "'***.cpp' '***.cppm' '***.cxx' '***.cxxm' '***.h++' '***.inl' '***.ipp' "
    "'***.ixx' '***.pcc' '***.tcc' '***.tpp' '***.H' '***.h' '***.hh' '***.hpp' "
    "'***.hxx' '***.py' '***.bash' '***.sh' '***.zsh' '***.ack' '***.al' '***.cpanfile' "
    "'***.makefile.pl' '***.perl' '***.ph' '***.plh' '***.plx' '***.pm' '***.psgi' "
    "'***.rexfile' '***.pl' '***.p6' '***.go' '***.HC'")
    
    output_file = f"{output_folder_path}/{vendor_branch_name}_code.txt"

    result = ""
    with open(output_file, "w+") as outfile:
        result = subprocess.run(
            ONLY_CODE_DIFF,
            shell=True,
            stdout=outfile,
            stderr=subprocess.PIPE, 
            text=True
        )

    JSON_CMD = "python3 ./json_dumper.py {}/{}.txt > {}/{}_aggregated.json".format(output_folder_path, vendor_branch_name, output_folder_path, vendor_branch_name)
    result = subprocess.run(JSON_CMD, shell=True, capture_output=True, text=True)
    JSON_CODE_CMD = "python3 ./json_dumper.py {}/{}_code.txt > {}/{}_aggregated_code.json".format(output_folder_path, vendor_branch_name, output_folder_path, vendor_branch_name)
    result = subprocess.run(JSON_CODE_CMD, shell=True, capture_output=True, text=True) 

if __name__ == "__main__":
    main()