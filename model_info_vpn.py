import requests
import sys
import gspread
import time
from bs4 import BeautifulSoup 
from lxml import html
import difflib
import random
import subprocess
import os
from http.client import RemoteDisconnected

from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException, ElementNotInteractableException 
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait 
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.firefox.service import Service

root_dir = os.getenv("KERNELS_ROOT_DIR")
directory = root_dir + '/mullvad/'
conf_files = [f for f in os.listdir(directory) if f.endswith('.conf')]

curr_vpn_setting = None

def get_driver_properties(driver):
    selenium_cookies = driver.get_cookies()
    cookies_dict = {cookie['name']: cookie['value'] for cookie in selenium_cookies}
    headers = {
        "User-Agent": driver.execute_script("return navigator.userAgent;"),
    }
    return headers, cookies_dict

def get_next_vpn_setting():
    return conf_files.pop(0)

def rotate_vpn():
    global curr_vpn_setting
    print("Old config: ", curr_vpn_setting)
    down_command = 'wg-quick down ' + directory + curr_vpn_setting
    subprocess.run(down_command, shell=True) 
    
    time.sleep(3)
    curr_vpn_setting = get_next_vpn_setting()
    print("New config: ", curr_vpn_setting)
    up_command = 'wg-quick up ' + directory + curr_vpn_setting
    subprocess.run(up_command, shell=True) 


def fetch_result_list(phone, url):
    driver = None
    options = Options()
    user_agent = "Mozilla/5.0 (X11; Linux x86_64; rv:115.0) Gecko/20100101 Firefox/115.0"
    options.set_preference("general.useragent.override", user_agent)

    decrypted_element = None

    while True:
        try:
            driver = webdriver.Firefox(options=options)
            driver.get(url)

            decrypted_element = driver.find_element(By.CSS_SELECTOR, "#decrypted")
            print("Element found!")
            break 

        except NoSuchElementException:
            print("Probably I'm banned, rotating VPN...")
            driver.quit()

            rotate_vpn()
            sleep_delay = 2 + random.randint(1, 15)
            time.sleep(sleep_delay)

    decrypted_content = decrypted_element.get_attribute('innerHTML')
    
    if decrypted_content is None:
        print('ERROR: decrypted content is none!')
        headers, cookies_dict = get_driver_properties(driver)
        driver.quit()
        return (None, headers, cookies_dict)

    soup = BeautifulSoup(decrypted_content, 'html.parser')
    ul = soup.find('ul')
    
    if ul is None:
        print("ERROR: no <ul> found for ", url)
        headers, cookies_dict = get_driver_properties(driver)
        driver.quit()
        return (None, headers, cookies_dict)

    li = ul.find_all('li')
    
    if li is None:
        print("ERROR: no <li> found for ", url)
        headers, cookies_dict = get_driver_properties(driver)
        driver.quit()
        return (None, headers, cookies_dict)


    li_list = list(li)
    print("Amount of li's: ", len(li_list))
    li_target_elem = None
    
    if len(li_list) > 1:
        print('Looking for closest name match')
        variants_list = []
        for li in li_list:
            a_tag = li.find('a')
            found_phone_name = a_tag.find('span').get_text(separator=" ")
            print("Matches? ", found_phone_name)
            variants_list.append(found_phone_name)
        print("VARIANTS LIST: ", variants_list)
        best_match = difflib.get_close_matches(phone, variants_list, 1, 0.8)
        print("BEST MATCH: ", best_match)
        if len(best_match) == 0:
            headers, cookies_dict = get_driver_properties(driver)
            driver.quit()
            return (None, headers, cookies_dict)
        for li in li_list:
            a_tag = li.find('a')
            found_phone_name = a_tag.find('span').get_text(separator=" ")
            print('Found phone name: ', found_phone_name)
            print('Best match: ', best_match)
            if found_phone_name == best_match[0]:
                link = a_tag['href']
                print("Returning link: ", link)
                headers, cookies_dict = get_driver_properties(driver)
                driver.quit()
                return (link, headers, cookies_dict)
    else:
        li_target_elem = li_list[0]
        a_tag = li_target_elem.find('a')
        phone_name = a_tag.find('span').get_text(separator=" ")
        link = a_tag['href']
        print("Phone name: ", phone_name, " href: ", link)
        headers, cookies_dict = get_driver_properties(driver)
        driver.quit()
        return (link, headers, cookies_dict)

    headers, cookies_dict = get_driver_properties(driver)
    driver.quit()
    return (None, headers, cookies_dict)


def construct_search_string(phone_name):
    query = phone_name.replace(" ", "+")
    url = "https://www.gsmarena.com/res.php3?sSearch=" + query
    return url

def corresp_names(model_name, data):
    entry_set = set()
    print("Amount of entries for ", model_name, ": ", len(data[model_name]))
    for entry in data[model_name]:
        brand = entry.get('brand')
        if brand.lower() != sheet.title.lower():
            if brand.lower() not in related and sheet.title.lower() not in related:
                print("Brand ", brand.lower(), " does not correspond to the sought ", sheet.title.lower())
                continue
        if brand == 'Redmi':
            brand = 'Xiaomi ' + brand
        elif brand == 'Xiaomi':
            brand = ""
        name = entry.get('name')
        oem_dev = ''
        if brand != "":
            oem_dev = brand + ' ' + name
        else:
            oem_dev = name
        entry_set.add(oem_dev)
    return entry_set



#CODE START

if __name__ == "__main__":
    if len(sys.argv) < 2:
        raise ValueError("Usage: python3 dump_to_sheets.py <table name> <vendor folder 1> <vendor folder 2>...")
    table_name = sys.argv[1]

    url = 'https://raw.githubusercontent.com/androidtrackers/certified-android-devices/refs/heads/master/by_device.json'
    response = requests.get(url, timeout = 5)
    data = None

    if response.status_code == 200:
        data = response.json()
    else:
        print("Could not retrieve the model json! Status code: ", response.status_code)
        sys.exit()

    related = ['xiaomi', 'redmi', 'poco']

    #TODO:KEEEEEEEEP!
    #curr_vpn_setting = get_next_vpn_setting()
    #print("Initial vpn config: ", curr_vpn_setting)
    #up_command = 'wg-quick up ' + directory + curr_vpn_setting
    #subprocess.run(up_command, shell=True) 
    #time.sleep(3)

    gc = gspread.service_account()
    sh = gc.open(table_name)

    worksheet_list = sh.worksheets()
    print(worksheet_list)
    for sheet in worksheet_list:
        worksheet = sh.worksheet(sheet.title)
        print(sheet.title)
        row_counter = 1
        model_names = worksheet.col_values(1)
        model_names = model_names[row_counter-1:]
        print("MODEL NAMES: ", model_names)
        for model_name in model_names:
            key = model_name if model_name in data else model_name.upper() if model_name.upper() in data else None
            if key:
                print(key, " entry found!")
                entry_set = corresp_names(model_name, data)
                print("Size of set: ", len(entry_set)) #we consider all phones with this fw
                for phone in entry_set:
                    print(phone)
                    search_url = construct_search_string(phone)
                    sleep_delay = 10 + random.randint(1, 15)
                    time.sleep(sleep_delay)
                    link_to_parse, headers, cookies_dict = fetch_result_list(phone, search_url)
                    if link_to_parse is not None:
                        link_to_parse = 'https://www.gsmarena.com/' + link_to_parse
                        print("Parsing: ", link_to_parse)
                        sleep_delay = 10 + random.randint(1, 15)
                        time.sleep(sleep_delay)
                        #phone_page = requests.get(link_to_parse, headers=headers, cookies=cookies_dict)
                        phone_page = requests.get(link_to_parse)
                        if phone_page.status_code == 200:
                            phone_soup = BeautifulSoup(phone_page.content, 'lxml')
                            title_elem = phone_soup.find("h1", {"class": "specs-phone-name-title"})
                            date_elem = phone_soup.find("span", {"data-spec": "released-hl"})
                            chipset_elem = phone_soup.find("td", {"data-spec": "chipset"})
                            print(title_elem.text)
                            title_cell = 'M' + str(row_counter)
                            print('Dying here (hopefully not)')
                            try:
                                worksheet.update_acell(title_cell, title_elem.text)
                            except Exception as e:
                                    try:
                                        gc = gspread.service_account()  # Re-authenticate with the Google Sheets API
                                        sh = gc.open(table_name)
                                        worksheet = sh.worksheet(sheet.title)
                                        worksheet.update_acell(title_cell, title_elem.text)
                                    except Exception as e:
                                        print(f"Error reconnecting to Google Sheets: {e}")
                                        sys.exit()
                            release = date_elem.text
                            if release.startswith("Released"):
                                release = release[len("Released "):] 
                            print(release)
                            release_cell = 'N' + str(row_counter)
                            worksheet.update_acell(release_cell, release)
                            print(chipset_elem.text)
                            chipset_cell = 'O' + str(row_counter)
                            worksheet.update_acell(chipset_cell, chipset_elem.text)
                        else:
                            print("ERROR: could not open ", link_to_parse)
            else:
                print('ERROR: device ', model_name, ' not found!')
            row_counter = row_counter + 1
        print('\n\n\n')