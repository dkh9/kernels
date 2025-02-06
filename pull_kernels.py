import gitlab
import base64 
import subprocess 
import os
import shutil
import re
import sys

gl = gitlab.Gitlab(url='https://dumps.tadiphone.dev/')

oem_list = ["samsung"]
oem_groups = []
visited_projs = []
root_dir = os.getenv("KERNELS_ROOT_DIR")

def parse_linux_version(s):
    match = re.search(r"Linux version (\d+\.\d+\.\d+)(\+?)", s)
    if match:
        version = match.group(1)
        plus_found = bool(match.group(2))  # True if '+' is found, False otherwise
        return version, plus_found
    return None, False

groups = gl.groups.list(all=True)
print("Available Groups:", groups)
for group in groups:
    if group.name in oem_list:
        oem_groups.append(group)
        print(f"Group ID: {group.id}, Name: {group.name}")

for group in oem_groups:
    print(f"\nProjects in group {group.name}:")
    if not os.path.exists(group.name):
        os.makedirs(group.name)
    os.chdir(group.name)
    projects = group.projects.list(all=True)

    for project in projects:
        if project in visited_projs:
            continue
        print(f"Project ID: {project.id}, Name: {project.name}")
        if not os.path.exists(project.name):
            os.makedirs(project.name)
        os.chdir(project.name)
        repo = gl.projects.get(project.id)
        branch_name = repo.default_branch
        try:
            file_content = repo.files.get(file_path='boot.img', ref=branch_name)
            binary_data = base64.b64decode(file_content.content)
            with open("orig-boot.img", "wb") as file:
                file.write(binary_data)
            command = 'vmlinux-to-elf orig-boot.img orig-boot.elf'
            try:
                subprocess.run(command, shell=True)      
            except Exception as e:
                print("Error: could not convert to elf!")
                os.chdir('..')
                continue
            baseline = "5.10.0"
            command = 'strings orig-boot.elf | grep -i "linux version"'
            result = subprocess.run(command, shell=True, capture_output=True, text=True)
            version_str = result.stdout
            android_version_match = re.search(r"-android(\d+)", version_str)
            android_version = android_version_match.group(1) if android_version_match else None
            
            version_match = parse_linux_version(version_str)
            kernel_version = version_match[0]
            if version_match[1] == True:
                kernel_version = kernel_version[:-1]
            
            if kernel_version is not None:
                print(kernel_version)
            else:
                print('COULD NOT RETRIEVE KERNEL VERSION')
                os.chdir('..')
                continue
            baseline_parts = list(map(int, baseline.split(".")))
            curr_parts = list(map(int, kernel_version.split(".")))
            if curr_parts < baseline_parts:
                print("Version not fitting! Leaving")
                os.chdir('..')
                shutil.rmtree(project.name)
                continue
            else:
                print('Version new enough!')
                scraper_command = ["python3", root_dir + "/gki_scrape.py", "orig-boot.elf"]
                result = subprocess.run("ls; pwd", shell=True, capture_output=True, text=True)
                print("LS & PWD:", result.stdout)

                process = subprocess.Popen(
                scraper_command,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,  
                text=True,  
                bufsize=1  
                )

                for line in iter(process.stdout.readline, ''):
                    print(line, end='')
                process.stdout.close()
                process.wait() 

                os.system('cd ../')
        except gitlab.exceptions.GitlabGetError as e:
            print(f"Error retrieving 'boot.img' from {project.name}: {e}")
        os.chdir('..')
    os.chdir('..')