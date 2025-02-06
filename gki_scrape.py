from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException, ElementNotInteractableException 
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait 
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.firefox.service import Service

import time
import re
import requests
from bs4 import BeautifulSoup
import subprocess
import sys, os
from datetime import datetime
from dateutil.relativedelta import relativedelta
from enum import Enum

class Artifact(Enum):
    boot = 1
    Image = 2

branch = "https://ci.android.com/builds/branches/aosp_kernel-common-android13-5.10-2023-11/grid?legacy=1"

def call_selenium_download(download_dir, url):
    print('Downloading to download dir:')
    print(download_dir)

    options = Options()
    #options.add_argument("--headless")
    options.set_preference("browser.download.folderList", 2)  # Use custom download path (2 = custom)
    options.set_preference("browser.download.manager.showWhenStarting", False)
    options.set_preference("browser.download.dir", download_dir)  # Custom download directory
    options.set_preference("browser.helperApps.neverAsk.saveToDisk", "application/octet-stream,application/x-gzip,application/zip,application/x-tar,application/x-7z-compressed,application/gzip")  # MIME types
    driver = webdriver.Firefox(options=options)
    try:
        driver.get(url)
        time.sleep(75)

    finally:
        driver.quit()

def download_boot_img_or_Image(build_page_link):
    page = requests.get(build_page_link, allow_redirects=True)
    if page.status_code == 200:
        curdir = os.getcwd()
        if '"name":"boot.img"' in page.text:
            call_selenium_download(curdir, build_page_link+'/boot.img')
            return Artifact.boot
        elif '"name":"Image"' in page.text:
            call_selenium_download(curdir, build_page_link+'/Image')
            return Artifact.Image
    else:
        return None     

def choose_aarch64_build(driver):
    driver.execute_script('''
        document.querySelector("#grid_page")
        .shadowRoot.querySelector("div > build-grid")
        .shadowRoot.querySelector("div.results > div.header-row > div.empty-build > huckle-button.filter-icon").click();
    ''')

    time.sleep(1)

    all_entries = driver.execute_script('''
    return document.querySelector("#grid_page")
        .shadowRoot.querySelector("div > build-grid")
        .shadowRoot.querySelector("div.results > div.header-row > div.empty-build")
        .querySelector("#target-filter-dialog > div.target-list")
        .querySelectorAll("div.target-list-entry"); 
    ''')


    for entry in all_entries:
        if entry.text == 'kernel_aarch64':
            entry.click()
            break

    driver.execute_script('''
    document.querySelector("#grid_page")
        .shadowRoot.querySelector("div > build-grid")
        .shadowRoot.querySelector("div.results > div.header-row > div.empty-build")
        .querySelector("#target-filter-dialog > div.dialog-header-container > huckle-button.dialog-close-icon").click();
    ''')

def get_all_grids(driver):
    while True:
        try:
            time.sleep(3)
            button = driver.execute_script('''
            return document.querySelector("#grid_page")
                .shadowRoot.querySelector("div > build-grid")
                .shadowRoot.querySelector("div.load-more-bar > paper-button");
            ''')
            if button :
                button.click()
            else :
                print('Load more is not available!')
                driver.execute_script("window.scrollBy(0,document.body.scrollHeight);")
                break
        except ElementNotInteractableException:
            print('Load more is not available!')
            driver.execute_script("window.scrollBy(0,document.body.scrollHeight);")
            time.sleep(3)
            break

    all_grids = driver.execute_script('''
    return document.querySelector("#grid_page")
        .shadowRoot.querySelector("div > build-grid")
        .shadowRoot.querySelector("div.results").querySelectorAll("div.result-row");
    ''')
    if all_grids:
        print("\nGrid amount: ", len(all_grids))
        return all_grids
    else:
        print('No grids!')
        return []

def match_successful_build(driver, all_grids):
    for i, grid in reversed(list(enumerate(all_grids))):
        result_element = driver.execute_script('''
            let grid = arguments[0];  // Get the current grid passed as an argument
            let result = grid.querySelector(".result");  // Look for the element with class "result"
            return result ? result.outerHTML : null;  // Return the outerHTML of the result element, or null if not found
        ''', grid)

        if result_element is not None:
            if "successful cell result" in result_element:
                if "test error" not in result_element:
                    print("First good build")
                    match = re.search(r'href="([^"]+)"', result_element)
                    if match:
                        href_link = match.group(1)  # Extract the first matched href link
                        print(f"Extracted href link: {href_link}")
                        matched_build = 'https://ci.android.com' + href_link
                        return matched_build
                    else:
                        print("No href link found, continuing")
                else:
                    print("Test error!")
        else:
            print(f"No element with class 'result' found in grid {i+1}")
            return ''

def get_first_build(branch_link):
    driver = webdriver.Firefox()  # or webdriver.Firefox()
    driver.get(branch_link)
    time.sleep(4)
    download_result = None

    choose_aarch64_build(driver)
    all_grids = get_all_grids(driver)

    if all_grids == []:
        driver.quit()
        return download_result
        
    matched_build = ''
    matched_build = match_successful_build(driver, all_grids)
    if matched_build != '':
        download_result = download_boot_img_or_Image(matched_build) #provide here a return value

    driver.quit()
    return download_result

def check_by_build_number(build_number):
    result_dict = {"found": False, "artifact": None}
    potential_build_url = "https://ci.android.com/builds/submitted/" + build_number + "/kernel_aarch64/latest"
    print(potential_build_url)

    build_page = requests.get(potential_build_url)
    if build_page.status_code == 200:
        if '"artifacts":[]' in build_page.text:
            print('Build does not exist, fall back to best-effort search')
        else:
            print('Build match found right away, downloading artifacts')
            downloaded_result = download_boot_img_or_Image(potential_build_url)
            if downloaded_result is not None:
                result_dict["found"] = True
                result_dict["artifact"] = downloaded_result
    
    return result_dict

def create_branch_url(kernel_version, android_version, formatted_date):
    major_minor_version = ".".join(kernel_version.split(".")[:2])
    url = 'https://ci.android.com/builds/branches/aosp_kernel-common-android' + android_version + '-' + major_minor_version + '-' + formatted_date + '/grid?legacy=1'
    print(url)
    return url

def get_full_version(version_str):
    lines = version_str.strip().splitlines()
    actual_version_line = next(line for line in lines if line.startswith("Linux version") and "%s" not in line)
    extracted_version = actual_version_line.split(" (")[0]
    return extracted_version

def extract_image_version(target_vmlinux):
    
    command = 'strings ' + target_vmlinux + ' | grep -i "linux version"'
    result = subprocess.run(command, shell=True, capture_output=True, text=True)
    print(result.stdout)

    version_str = result.stdout

    version_match = re.search(r"Linux version (\d+\.\d+\.\d+)", version_str)
    android_version_match = re.search(r"-android(\d+)", version_str)
    build_number_match = re.search(r"\bab[0-9]+", version_str)  

    kernel_version = version_match.group(1) if version_match else None
    android_version = android_version_match.group(1) if android_version_match else None
    #date_match = re.search(r"\w+ \w+ \d+ \d+:\d+:\d+ \w+ \d+", version_str).group(0)
    pre_date_match = re.search(r"\w+\s+\w+\s+\d+\s+\d+:\d+:\d+\s+\w+\s+\d+", version_str)
    if pre_date_match is not None:
        date_match = pre_date_match.group(0)
    else:
        date_match = None
    build_number = build_number_match.group(0) if build_number_match else None
    if build_number is not None:
        build_number = build_number[2:]

    print("Version: ", kernel_version)              
    print("Android version: ", android_version)
    print("Build number: ", build_number)
    print("Build date: ", date_match)

    date_str_without_tz = " ".join(date_match.split()[:-2]) + " " + date_match.split()[-1]
    date_obj = datetime.strptime(date_str_without_tz, '%a %b %d %H:%M:%S %Y')
    formatted_date = date_obj.strftime('%Y-%m')
    print("Formatted date:", formatted_date)

    info_dict = {"kernel version" : kernel_version,
                "android version" : android_version,
                "build number" : build_number,
                "build date" : formatted_date,
                "build date obj" : date_obj}

    return info_dict



if __name__ == "__main__":
    do_best_effort_search = False
    n = len(sys.argv)
    if n < 2:
        print('Provide boot.img or vmlinux')
        sys.exit()
    target_vmlinux = sys.argv[1]
    version_info = extract_image_version(target_vmlinux)

    if version_info["build number"] is not None:
        build_num_check = check_by_build_number(version_info["build number"])
        if build_num_check["found"] == False:
            do_best_effort_search = True
        else:
            print("Downloaded corresponding image!")
            image_file = ''
            if build_num_check["artifact"] == Artifact.Image:
                image_file = 'Image'
            elif build_num_check["artifact"] == Artifact.boot:
                image_file = 'boot.img'

            command = 'vmlinux-to-elf ' + image_file + ' corresp-boot.elf'
            try:
                subprocess.run(command, shell=True, capture_output=True, text=True)
            except subprocess.CalledProcessError:
                print('Problem in vmlinux-to-elf!')
                sys.exit()

            command_orig = 'strings ' + target_vmlinux + ' | grep -i "linux version"'
            command_corresp = 'strings corresp-boot.elf | grep -i "linux version"'
            orig_ver_string = subprocess.run(command_orig, shell=True, capture_output=True, text=True).stdout
            corresp_ver_string = subprocess.run(command_corresp, shell=True, capture_output=True, text=True).stdout

            extracted_orig = get_full_version(orig_ver_string)
            extracted_corresp = get_full_version(corresp_ver_string)
            print("Extracted orig: ", extracted_orig)
            print("Extracted corresp: ", extracted_corresp)
            if extracted_orig == extracted_corresp:
                print("Kernels fully identical, success")
                expired_cycles = False
            else:
                print("Kernels not identical, NEEDS MANUAL CHECK IN LOGS!")
    else:
        print('Build number either not present or not extracted, fall back to best-effort search')
        do_best_effort_search = True

    if do_best_effort_search == True and version_info["build date"] is not None:
        expired_cycles = True
        initial_date = version_info["build date"]
        formatted_date = version_info["build date"]

        for i in range(1, 37):
            print("Starting best-effort cycle")
            continue_next_cycle = False

            branch_url =  create_branch_url(version_info["kernel version"], version_info["android version"], formatted_date) #provide max amount of searches
            download_result = get_first_build(branch_url)
            if download_result == Artifact.boot:
                subprocess.run('vmlinux-to-elf boot.img corresp-boot.elf', shell=True, text=True)
            elif download_result == Artifact.Image:
                subprocess.run('vmlinux-to-elf Image corresp-boot.elf', shell=True, text=True)
            else:
                print("Nothing downloaded!")
                continue_next_cycle = True

            if continue_next_cycle == False:
                corresp_version = extract_image_version('corresp-boot.elf')

                print("Orig version kernel: ", version_info["kernel version"] )
                print("Corresp version kernel: ", corresp_version["kernel version"])

                corresp_parts = list(map(int, corresp_version["kernel version"].split(".")))
                orig_parts = list(map(int, version_info["kernel version"].split(".")))

                if corresp_parts > orig_parts:
                    print("Corresponding version larger, removing, continuing search")
                    subprocess.run('rm corresp-boot.elf boot.img Image', shell=True)
                elif corresp_parts == orig_parts:
                    print("Corresponding version same, saving as last oldest")
                    subprocess.run('mv corresp-boot.elf corresp-boot-oldest.elf; rm boot.img Image', shell=True)
                else:
                    print("Corresponding version smaller, stopping, checking the oldest")
                    if os.path.exists('corresp-boot-oldest.elf'):
                        print("All good, identified the oldest, search finished")
                        subprocess.run('rm corresp-boot.elf boot.img Image', shell=True)
                    else:
                        print("Smaller version found, but no corresp-boot-oldest.elf exists, ABORT")
                    expired_cycles = False
                    break

            new_date_decremented = version_info["build date obj"] - relativedelta(months=1*i)
            formatted_date_decremented = new_date_decremented.strftime('%Y-%m')
            print(f"Decremented date: {formatted_date_decremented}")
            formatted_date = formatted_date_decremented

    if expired_cycles == True:
        print('CYCLES EXPIRED')


