"""
Schneider Electric (SE) has a unified interface for accessing software downloads: DOWNLOAD_URL_*.
One of the categories is 'firmware'.
Depending on the selected website region, the number of available downloads varies.
As of 22-11-06, region 'Global' (DOWNLOAD_URL_GLOBAL) provides the highest number of downloads, which is therefore
selected as default.

Even when category 'firmware' is selected, some displayed products are just release notes with no associated binary.
These products are therefore filtered out.
"""
import json
import re
from typing import Optional
from urllib.request import urlopen

from selenium import webdriver
from selenium.common import WebDriverException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions

from tqdm import tqdm
from webdriver_manager.chrome import ChromeDriverManager

from src.logger import create_logger
from src.Vendors.scraper import Scraper

DOWNLOAD_URL_GLOBAL = "https://www.tp-link.com/en/support/download/"


class TPLinkScraper(Scraper):
    def __init__(
        self,
        logger,
        scrape_entry_url: str = DOWNLOAD_URL_GLOBAL,
        headless: bool = True,
        max_products: int = float("inf"),
    ):
        self.logger = logger
        self.scrape_entry_url = scrape_entry_url
        self.headless = headless
        self.max_products = max_products
        self.name = "TPLink"

        chrome_options = Options()
        if self.headless:
            chrome_options.add_argument("--window-size=1920,1080")
            chrome_options.add_argument("--start-maximized")
            chrome_options.add_argument("--headless")
        self.driver = webdriver.Chrome(service=ChromeService(ChromeDriverManager().install()), options=chrome_options)
        # self.driver.implicitly_wait(0.5)  # has to be set only once

    def _scrape_product_metadata(self, product_url: str, product_category: str) -> dict:
        CSS_SELECTOR_FIRMWARE = "a[href='#Firmware']"
        CSS_SELECTOR_PRODUCT_NAME = "#model-version-name"
        CSS_SELECTOR_HARDWARE_VERSION = "#verison-hidden"
        CSS_SELECTOR_SOFTWARE_VERSION = "#content_Firmware > table > tbody > tr.basic-info > th.download-resource-name"
        CSS_SELECTOR_RELEASE_DATE = (
            "#content_Firmware > table > tbody > tr.detail-info > td:nth-child(1) > span:nth-child(2)"
        )
        CSS_SELECTOR_DOWNLOAD_LINK_SIMPLE = (
            "#content_Firmware > table > tbody > tr.basic-info > th.download-resource-btnbox > a"
        )
        CSS_SELECTOR_DOWNLOAD_LINK_GLOBAL = "#content_Firmware > table > tbody > tr.basic-info > th.download-resource-btnbox > div > div > div > a.tp-dialog-btn.tp-dialog-btn-white.ga-click"

        # access product page
        try:
            self.driver.get(product_url)
        except WebDriverException as e:
            self.logger.warning(f"Could not access product URL '{product_url}'.")
            return {}

        # check if firmware download is offered
        try:
            self.driver.find_element(by=By.CSS_SELECTOR, value=CSS_SELECTOR_FIRMWARE).click()
        except WebDriverException as e:
            self.logger.info(f"No firmware found for product URL '{product_url}'.")
            return {}

        product_name = version = release_date = download_link = None

        # scrape product name
        try:
            product_name = self.driver.find_element(by=By.CSS_SELECTOR, value=CSS_SELECTOR_PRODUCT_NAME).text
            hardware_version = self.driver.find_element(by=By.CSS_SELECTOR, value=CSS_SELECTOR_HARDWARE_VERSION).text
            product_name = product_name + hardware_version
        except WebDriverException as e:
            self.logger.debug(f"Couldn't scrape product name for '{product_url}'.")

        # scrape version
        try:
            resource_name = self.driver.find_element(by=By.CSS_SELECTOR, value=CSS_SELECTOR_SOFTWARE_VERSION).text
            version = "_".join(resource_name.split("_")[1:])  # remove product name from version
        except Exception as e:
            self.logger.debug(f"Couldn't scrape version for '{product_url}'.")

        # scrape release date
        try:
            release_date = self.driver.find_element(by=By.CSS_SELECTOR, value=CSS_SELECTOR_RELEASE_DATE).text.rstrip()
        except Exception as e:
            self.logger.debug(f"Couldn't scrape release date for '{product_url}'.")

        # scrape download link
        try:
            download_link = self.driver.find_element(
                by=By.CSS_SELECTOR, value=CSS_SELECTOR_DOWNLOAD_LINK_GLOBAL
            ).get_attribute("href")
        except WebDriverException as e:
            try:
                download_link = self.driver.find_element(
                    by=By.CSS_SELECTOR, value=CSS_SELECTOR_DOWNLOAD_LINK_SIMPLE
                ).get_attribute("href")
            except:
                self.logger.debug(f"Couldn't scrape download link for '{product_url}'.")

        return {
            "manufacturer": "TP-Link",
            "product_name": product_name,
            "product_type": product_category,
            "version": version,
            "release_date": release_date,
            "checksum_scraped": None,
            "download_link": download_link,
            "additional_data": {},
        }

    def scrape_metadata(self) -> list[dict]:
        CSS_SELECTOR_CLOSE_SWITCH_REGION = "body > div.page-content-wrapper > div.tp-local-switcher > div > span"
        CSS_SELECTOR_PRODUCT_CATEGORIES = "#list > div.item"
        CSS_SELECTOR_PRODUCT_CATEGORIES_NAME = "h2 > span.tp-m-hide"
        CSS_SELECTOR_PRODUCT_LINKS = "div.item-box > span > a"

        self.logger.info(f"Start scraping metadata of firmware products.")
        try:
            self.driver.get(self.scrape_entry_url)
            self.logger.info(f"Successfully accessed entry point URL {self.scrape_entry_url}.")
        except WebDriverException as e:
            self.logger.error(f"Could not access entry point URL {self.scrape_entry_url}. Abort scraping.\n{e}")
            return []

        # when first accessing the website, an overlay window asking to switch to the correct region might block other
        # elements; close this overlay
        try:
            self.driver.find_element(by=By.CSS_SELECTOR, value=CSS_SELECTOR_CLOSE_SWITCH_REGION).click()
        except WebDriverException as e:
            pass

        try:
            product_categories_el = self.driver.find_elements(by=By.CSS_SELECTOR, value=CSS_SELECTOR_PRODUCT_CATEGORIES)
        except WebDriverException as e:
            self.logger.error(f"Could not scrape product categories. Abort scraping.\n{e}")
            return []

        product_categories = {}
        for category in product_categories_el:
            try:
                product_category_name = category.find_element(
                    by=By.CSS_SELECTOR, value=CSS_SELECTOR_PRODUCT_CATEGORIES_NAME
                ).text
                product_urls = [
                    el.get_attribute("href")
                    for el in category.find_elements(by=By.CSS_SELECTOR, value=CSS_SELECTOR_PRODUCT_LINKS)
                ]
                print(product_urls)
                product_categories[product_category_name] = product_urls
            except WebDriverException as e:
                pass

        extracted_data = []
        for category in product_categories:
            if len(extracted_data) >= self.max_products:
                break
            for url in product_categories[category]:
                if product_metadata := self._scrape_product_metadata(url, category):
                    extracted_data.append(product_metadata)
                    if len(extracted_data) >= self.max_products:
                        break

        self.logger.info(f"Finished scraping metadata of firmware products. Return metadata to core.")
        return extracted_data


if __name__ == "__main__":
    logger = create_logger(level="INFO")

    scraper = TPLinkScraper(logger, DOWNLOAD_URL_GLOBAL, max_products=10, headless=False)

    firmware_data = scraper.scrape_metadata()
    with open("../../../scraped_metadata/firmware_data_tp-link.json", "w") as firmware_file:
        json.dump(firmware_data, firmware_file)
