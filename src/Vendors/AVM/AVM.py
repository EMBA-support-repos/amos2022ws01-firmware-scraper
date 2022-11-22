"""
Scraper module for AVM vendor
"""

from os import path
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from urllib.request import urlopen
import ftputil
import requests
import sys
import pandas as pd


class AVMScraper:

    def __init__(
        self
    ):
        self.url = "https://download.avm.de"
        self.name = "AVM"
        self.driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()))
        self.fw_types = [".image", ".exe", ".zip", ".dmg"]
        self.catalog = []

    def connect_webdriver(self):
        try:
            self.driver.get(self.url)
            logger.info("Connected Successfully!")
        except Exception as e:
            logger.info(e + ": Could not connect to AVM!")

    # List available firmware downloads
    def scrape_metadata(self) -> list:
        
        # Get all links on index page
        logger.info(f"Scraping all data from {self.url}")

        elem_list = self.driver.find_elements(By.XPATH, "//pre/a")
        elem_list = ["/" + elem.text for elem in elem_list if elem.text not in ["../", "archive/"]]
        
        # Iterate through index links and append all subdirectories
        for index, value in enumerate(elem_list):
            logger.debug(f"Searching {value}")
            self.driver.get(self.url + value)
            sub_elems = self.driver.find_elements(By.XPATH, "//pre/a")

            fw_files = ([elem.get_property("pathname") for elem in sub_elems if self._get_file_extension(elem.get_property("pathname")) in self.fw_types])
            for file in fw_files: 

                firmware_item = {"manufacturer": "AVM",
                "product_name": None,
                "product_type": None,
                "version": None,
                "release_date": None,
                "download_link": None,
                "checksum_scraped": None,
                "additional_data": {}
                }
                
                logger.debug(f"Found firmware file: {file}")
                text_file = next((elem.get_property("pathname") for elem in sub_elems if elem.get_property("innerHTML") == "info_en.txt"), None)
                if text_file:
                    logger.debug(f"Found info file: {text_file}")
                    product, release_date, version = self._parse_txt_file(self.url + text_file)
                    firmware_item["product_name"] = product
                    firmware_item["release_date"] = release_date
                    firmware_item["version"] = version
                    firmware_item["additional_data"] = {"info_url": self.url + text_file}
                firmware_item["download_link"] = self.url + file
                firmware_item["product_type"] = value.strip("/").split("/")[0]
                self.catalog.append(firmware_item)
            
            sub_elems = [elem.get_property("pathname") for elem in sub_elems if elem.text != "../" and self._get_file_extension(elem.get_property("pathname")) not in [".txt", ".image", ".exe", ".zip", ".dmg"]]
            elem_list.extend(sub_elems)
        return self.catalog
 
    def scrape_metadata_via_ftp(self):

        dict_ = {}

        with ftputil.FTPHost("ftp.avm.de", "anonymous", "") as ftp_host:

            products = ftp_host.listdir(ftp_host.curdir)
            products.remove("archive")
            for product in products:
                for root, dirs, files in ftp_host.walk(product):
                    if not any(_ for _ in files if self.get_file_extension(_)=='.image'):
                        continue
                    else:
                        if not any(_ for _ in files if self.get_file_extension(_)=='.txt'):
                            print("No info.txt available.")
                            dict_["manufacturer"].append("AVM")
                            dict_["product_name"].append(root.split("/")[1])
                            dict_["product_type"].append("NA")
                            dict_["version"].append("NA")
                            dict_["release_date"].append("NA")
                            dict_["checksum_scraped"].append("NA")
                            dict_["download_link"].append("NA")
                            dict_["additional_data"] = {}
                        else:
                            for f in files:
                                if f == "info_en.txt":
                                    txt = self.read_txt_file(f)
               
    def _get_file_extension(self, filename):
        return path.splitext(filename)[-1]

    # TODO: Parse text files other than info_txt.en
    def _parse_txt_file(self, file_url: str):

        product, release_date, version = None, None, None
        try:
            #import pdb;pdb.set_trace()
            txt = requests.get(file_url).text.splitlines()
            product = self._get_partial_str(txt, "Product").split(":")[-1].strip()
            release_date = self._get_partial_str(txt, "Release").split(":")[-1].strip()
            version = self._get_partial_str(txt, "Version").split(":")[-1].strip()
            logger.debug(f"Found {product, release_date, version} in txt file!")
        except Exception as e:
            logger.debug(f"Could not parse text file: {e}")

        return product, release_date, version
    
    def _get_partial_str(self, txt: list, query: str):
        return [s for s in txt if query in s][0]

    # Download firmware
    def download_firmware(self, filename: str, target_dir: str):
        pass
        
if __name__ == '__main__':

    import logging
    from utils import setup_logger

    logger = setup_logger()
    AVM = AVMScraper()
    AVM.connect_webdriver()
    catalog = AVM.scrape_metadata()
    logger.info(catalog)
    