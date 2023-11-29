from ..exceptions import UnknownOSException, ChromeError
from .common import NO_CHROME_DRIVER
from clint.textui import puts, colored
from selenium import webdriver
from selenium.common.exceptions import WebDriverException
from shutil import which
from urllib.request import urlretrieve
from appdirs import AppDirs
from ..version import version
from os.path import exists

import os, sys, stat, platform
import subprocess
import progressbar
import re
import zipfile
import requests
import pathlib

cache_dir = AppDirs("DeleteFB", version=version).user_cache_dir

try:
    pathlib.Path(cache_dir).mkdir(parents=True, exist_ok=True)
except FileExistsError:
    pass

def extract_zip(filename, chrome_maj_version):
    """
    Uses zipfile package to extract a single zipfile
    :param filename:
    :return: new filename
    """

    # Remove any leftover unversioned chromedriver
    try:
        os.remove(f"{cache_dir}/chromedriver")
    except FileNotFoundError:
        pass

    try:
        _file = zipfile.ZipFile(filename, 'r')
    except FileNotFoundError:
        puts(colored.red(f"{filename} Does not exist"))
        sys.exit(1)

    # Save the name of the new file
    new_file_name = None

    # Extract the file and make it executable
    _file.extractall(path=cache_dir)

    # Check if chromedriver.exe is in a subdirectory
    driver_folder = os.path.join(cache_dir, f"chromedriver{chrome_maj_version}")
    if os.path.exists(driver_folder) and os.path.isfile(os.path.join(driver_folder, "chromedriver.exe")):
        new_file_name = os.path.join(driver_folder, "chromedriver.exe")
    elif os.path.exists(os.path.join(cache_dir, "chromedriver.exe")):
        new_file_name = os.path.join(cache_dir, "chromedriver.exe")

    if new_file_name is None:
        raise ChromeError("Failed to find chromedriver.exe after extraction")

    driver_stat = os.stat(new_file_name)
    os.chmod(new_file_name, driver_stat.st_mode | stat.S_IEXEC)

    _file.close()
    os.remove(filename)
    return new_file_name


def setup_selenium(options, chrome_binary_path):
    try:
        # try letting Selenium find the driver (in PATH)
        return webdriver.Chrome(options=options)
    except WebDriverException:
        # Configures selenium to use a custom path
        driver_path = get_webdriver(chrome_binary_path)
        return webdriver.Chrome(executable_path=driver_path, options=options)

def parse_version(output):
    """
    Attempt to extract version number from chrome version string.
    """
    return [c for c in re.split('([0-9]+)\.?', output.decode("utf-8")) if all(d.isdigit() for d in c) and c][0]

def get_chrome_version():
    print(f"{os.name}")
    try:
        # The command to retrieve Chrome version on all platforms
        if os.name == 'nt':  # For Windows
            command = 'reg query "HKEY_CURRENT_USER\Software\Google\Chrome\BLBeacon" /v version'
            result = subprocess.check_output(command, shell=True).decode("utf-8")
            version_line = result.strip().split('\n')[-1]
            version = version_line.split()[2]
        else:  # For macOS and Linux
            command = 'google-chrome --version'
            result = subprocess.check_output(command.split()).decode("utf-8").strip()
            version = result.split(' ')[2]
        return version
    except Exception as e:
        return f"Error: {e}"
    
def construct_driver_url(chrome_binary_path=None):
    """
    Construct a URL to download the Chrome Driver.
    """

    platform_string = platform.system()
    chrome_drivers = {
        "Windows" : "https://edgedl.me.gvt1.com/edgedl/chrome/chrome-for-testing/{0}/win64/chromedriver-win64.zip",
        "Darwin" : "https://edgedl.me.gvt1.com/edgedl/chrome/chrome-for-testing/{0}/mac-x64/chromedriver-mac-x64.zip",
        "Linux" : "https://edgedl.me.gvt1.com/edgedl/chrome/chrome-for-testing/{0}/linux64/chromedriver-linux64.zip"
    }

    version = get_chrome_version()

    if version is None:
        raise ChromeError("Chrome version not found")

    # Split the version string into parts using the dot as a delimiter
    parts = version.split('.')

    # Make the last number after the 3rd dot be ...
    parts[3] = '105'

    # Join the parts back together using the dot as a delimiter
    modified_version = '.'.join(parts)

    return version, chrome_drivers.get(platform_string).format(modified_version)

def get_webdriver(chrome_binary_path):
    """
     Ensure a webdriver is available
     If Not, Download it.
    """

    # Download it according to the current machine
    chrome_maj_version, chrome_webdriver = construct_driver_url(chrome_binary_path)

    #windows location
    driver_path = f"{cache_dir}\chromedriver-win64\chromedriver"

    if exists(driver_path):
        return driver_path

    if not chrome_webdriver:
        raise UnknownOSException("Unknown Operating system platform")

    global total_size

    def show_progress(*res):
        global total_size
        pbar = None
        downloaded = 0
        block_num, block_size, total_size = res

        if not pbar:
            pbar = progressbar.ProgressBar(maxval=total_size)
            pbar.start()
        downloaded += block_num * block_size

        if downloaded < total_size:
            pbar.update(downloaded)
        else:
            pbar.finish()

    puts(colored.yellow("Downloading Chrome Webdriver"))
    file_name = f"{cache_dir}/{chrome_webdriver.split('/')[-1]}"
    response = urlretrieve(chrome_webdriver, file_name, show_progress)

    if int(response[1].get("Content-Length")) == total_size:
        puts(colored.green("Completed downloading the Chrome Driver."))

        return extract_zip(file_name, chrome_maj_version)

    else:
        puts(colored.red("An error Occurred While trying to download the driver."))
        # remove the downloaded file and exit
        os.remove(file_name)
        sys.stderr.write(NO_CHROME_DRIVER)
        sys.exit(1)