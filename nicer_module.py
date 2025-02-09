'''cp -r /path/to/repo1/* .
git checkout -b branch1
git add .
git commit -m "Add codebase from repo1"

# Add the second codebase
rm -rf *
cp -r /path/to/repo2/* .
git checkout -b branch2
git add .
git commit -m "Add codebase from repo2"'''


#redo to:
'''
git checkout -b branch1
rm -rf ./*
cp -r /path/to/repo1/* .
git add .
git commit -m "Add codebase from repo1"
'''


import os
import sys
import subprocess
import shutil

TEST_COMMAND="git checkout -b "
EXISTING_BRANCH_COMMAND = "git checkout -f "
COMPARE_SOURCES_DIR="/home/dasha/k-pop/codebase-comparison"
COPY_COMMAND = "cp -r "

def clear_directory(dir_path):
    # Ensure the path exists and is a directory
    if not os.path.exists(dir_path) or not os.path.isdir(dir_path):
        raise ValueError(f"Invalid directory path: {dir_path}")
    
    # Iterate over each item in the directory
    for item in os.listdir(dir_path):
        if item.startswith("."):
            continue
        item_path = os.path.join(dir_path, item)
        # Check if item is a file or directory
        if os.path.isfile(item_path) or os.path.islink(item_path):
            os.unlink(item_path)  # Remove file or symlink
        elif os.path.isdir(item_path):
            shutil.rmtree(item_path)  # Remove directory and its contents

# Example usage


def main():
    # Ensure two command-line arguments are provided
    if len(sys.argv) != 3:
        print("Usage: nicer_module.py <gki_branch_name> <vendor_branch_name>")
        sys.exit(1)
    
    # Get command-line arguments
    gki_branch_name = sys.argv[1]
    vendor_branch_name = sys.argv[2]

    # Get environment variables
    gki_path = os.getenv("GKI")
    vendor_path = os.getenv("VENDOR")

    # Check if environment variables are set
    if gki_path is None or vendor_path is None:
        print("Error: Environment variables GKI and VENDOR must be set.")
        sys.exit(1)
    
    # Print or use the variables as needed
    print(f"GKI Branch Name: {gki_branch_name}")
    print(f"Vendor Branch Name: {vendor_branch_name}")
    print(f"GKI Path: {gki_path}")
    print(f"Vendor Path: {vendor_path}")

    ##VERY IMPORTANT TO HAVE HERE!
    os.chdir(COMPARE_SOURCES_DIR)
    result = subprocess.run(TEST_COMMAND + "gki_" + gki_branch_name, shell=True, capture_output=True, text=True)
    if "already exists" in result.stderr:
        print("Already exists!")
        result = subprocess.run(EXISTING_BRANCH_COMMAND + "gki_" + gki_branch_name, shell=True, capture_output=True, text=True)
    elif "Switched to a new branch" in result.stderr:
        print("Branch did not exist!")
        clear_directory(COMPARE_SOURCES_DIR)
        print("Cleared directory")
        FULL_COPY_GKI_CMD = '{} {}/* . ; git add . ; git commit -m "Add codebase from {}"'.format(COPY_COMMAND, gki_path, gki_branch_name) 
        print("FULL COPY GKI CMD: ", FULL_COPY_GKI_CMD)
        result = subprocess.run(FULL_COPY_GKI_CMD, shell=True, capture_output=True, text=True)
    else: 
        print("Something weird happened")
        sys.exit()


    

    ##VERY IMPORTANT TO HAVE HERE!
    os.chdir(COMPARE_SOURCES_DIR)
    result = subprocess.run(TEST_COMMAND + "vendor_" + vendor_branch_name, shell=True, capture_output=True, text=True)
    if "already exists" in result.stderr:
        print("Already exists!")
        result = subprocess.run(EXISTING_BRANCH_COMMAND + "vendor_" + vendor_branch_name, shell=True, capture_output=True, text=True)
    elif "Switched to a new branch" in result.stderr:
        print("Branch did not exist!")
        clear_directory(COMPARE_SOURCES_DIR)
        print("Cleared directory")
        FULL_COPY_VENDOR_CMD = '{} {}/* . ; git add . ; git commit -m "Add codebase from {}"'.format(COPY_COMMAND, vendor_path, vendor_branch_name) 
        result = subprocess.run(FULL_COPY_VENDOR_CMD, shell=True, capture_output=True, text=True)
    else: 
        print("Something weird happened")
        sys.exit()

   

    DIFF_CMD = "git diff {} {} --numstat > ../oppo_better/{}.txt".format("gki_"+gki_branch_name, "vendor_"+vendor_branch_name, vendor_branch_name)
    result = subprocess.run(DIFF_CMD, shell=True, capture_output=True, text=True)
    #ONLY_CODE_DIFF = "git diff {} {} --numstat -- '***.a51' '***.asm' '***.nasm' '***.S' '***.s' '***.c' '***.cats' '***.ec' '***.idc' '***.pgc',  '***.C' '***.c' '***.c++m' '***.cc' '***.ccm' '***.CPP' '***.cpp' '***.cppm' '***.cxx' '***.cxxm' '***.h++' '***.inl' '***.ipp' '***.ixx' '***.pcc' '***.tcc' '***.tpp' '***.H' '***.h' '***.hh' '***.hpp' '***.hxx' '***.py' '***.bash' '***.sh' '***.zsh' '***.ack' '***.al' '***.cpanfile' '***.makefile.pl' '***.perl' '***.ph' '***.plh' '***.plx' '***.pm' '***.psgi'  '***.rexfile' '***.pl' '***.p6' '***.go' '***.HC' > ../oppo_better/{}_code.txt".format("gki_"+gki_branch_name, "vendor_"+vendor_branch_name, vendor_branch_name)
    
    ONLY_CODE_DIFF = (
    f"git diff gki_{gki_branch_name} vendor_{vendor_branch_name} --numstat "
    "'***.a51' '***.asm' '***.nasm' '***.S' '***.s' '***.c' '***.cats' '***.ec' "
    "'***.idc' '***.pgc' '***.C' '***.c' '***.c++m' '***.cc' '***.ccm' '***.CPP' "
    "'***.cpp' '***.cppm' '***.cxx' '***.cxxm' '***.h++' '***.inl' '***.ipp' "
    "'***.ixx' '***.pcc' '***.tcc' '***.tpp' '***.H' '***.h' '***.hh' '***.hpp' "
    "'***.hxx' '***.py' '***.bash' '***.sh' '***.zsh' '***.ack' '***.al' '***.cpanfile' "
    "'***.makefile.pl' '***.perl' '***.ph' '***.plh' '***.plx' '***.pm' '***.psgi' "
    "'***.rexfile' '***.pl' '***.p6' '***.go' '***.HC'")

    #result = subprocess.run(ONLY_CODE_DIFF, shell=True, capture_output=True, text=True)
    
    output_file = f"../oppo_better/{vendor_branch_name}_code.txt"

# Run the command and redirect to a file manually
    result = ""
    with open(output_file, "w") as outfile:
        result = subprocess.run(
            ONLY_CODE_DIFF,
            shell=True,
            stdout=outfile,
            stderr=subprocess.PIPE,  # Capture errors
            text=True
        )

    print("ONLY CODE DIFF RES: ", result.stderr)
    JSON_CMD = "python3 /home/dasha/k-pop/json_dumper_huh.py ../oppo_better/{}.txt > ../oppo_better/{}_aggregated.json".format(vendor_branch_name, vendor_branch_name)
    result = subprocess.run(JSON_CMD, shell=True, capture_output=True, text=True)
    JSON_CODE_CMD = "python3 /home/dasha/k-pop/json_dumper_huh.py ../oppo_better/{}_code.txt > ../oppo_better/{}_aggregated_code.json".format(vendor_branch_name, vendor_branch_name)
    result = subprocess.run(JSON_CODE_CMD, shell=True, capture_output=True, text=True) 

if __name__ == "__main__":
    main()


#("git diff {} {} --numstat -- '***.a51' '***.asm' '***.nasm' '***.S' '***.s' '***.c' '***.py'",
#"'***.cats' '***.ec' '***.idc' '***.pgc',  '***.C' '***.c' '***.c++m' '***.cc' '***.ccm' '***.CPP' '***.cpp' '***.cppm'", 
#"'***.cxx' '***.cxxm' '***.h++' '***.inl' '***.ipp' '***.ixx' '***.pcc' '***.tcc' '***.tpp' '***.H' '***.h' '***.hh' '***.hpp'",
#"'***.hxx'  '***.bash' '***.sh' '***.zsh' '***.ack' '***.al' '***.cpanfile' '***.makefile.pl' '***.perl' '***.ph'",
#"'***.plh' '***.plx' '***.pm' '***.psgi'  '***.rexfile' '***.pl' '***.p6' '***.go' '***.HC' > ../diff_better/{}_code.txt").format("gki_"+gki_branch_name, "vendor_"+vendor_branch_name, vendor_branch_name)