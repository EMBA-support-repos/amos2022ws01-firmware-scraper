import json

from selenium.common import WebDriverException
from selenium.webdriver.common.by import By

from src.logger import *
from src.Vendors.scraper import Scraper

DOWNLOAD_URL_EN = "https://www.swisscom.ch/en/residential/help/device/firmware.html"


class SwisscomScraper(Scraper):
    def __init__(
        self, driver, scrape_entry_url: str = DOWNLOAD_URL_EN, headless: bool = True, max_products: int = float("inf")
    ):
        self.logger = get_logger()
        self.scrape_entry_url = scrape_entry_url
        self.headless = headless
        self.name = "Swisscom"
        self.driver = driver
        self.driver.implicitly_wait(0.5)  # has to be set only once

    def _scrape_product_metadata(self, category_name: str, category_name_clean: str, product_id: str) -> dict:
        CSS_SELECTOR_SOFTWARE_VERSION = (
            "div:nth-child(5) > div > div > div > div > div.accordion__toggle > div.accordion__header > h4"
        )
        CSS_SELECTOR_DOWNLOAD_LINK = "span > div > a"

        product_category_url = f"{self.scrape_entry_url}#tab1={category_name}"
        product_url = product_category_url + f"&tab={product_id}"

        # access product category tab
        try:
            if self.driver.current_url != product_category_url:
                self.driver.get(product_category_url)
        except WebDriverException as e:
            self.logger.debug(
                f"Could not access product category tab '{product_url}'.")
            return {}

        product_name = version = download_link = product_div = None

        # scrape product div
        try:
            product_div = self.driver.find_element(
                by=By.CSS_SELECTOR, value=f"div[data-id='{product_id}']")
        except WebDriverException as e:
            self.logger.warning(attribute_scraping_failure(
                f"metadata for '{product_url}'"))
            return {}

        # scrape product name
        try:
            parent_el = self.driver.find_element(
                by=By.CSS_SELECTOR, value=f"a[data-track-label='{product_id}']")
            product_name = parent_el.find_element(
                by=By.CSS_SELECTOR, value="h6").text.strip()
        except WebDriverException as e:
            self.logger.debug(attribute_scraping_failure(
                f"product name for '{product_url}'"))

        # scrape download link
        try:
            download_link = product_div.find_element(
                by=By.CSS_SELECTOR, value=CSS_SELECTOR_DOWNLOAD_LINK
            ).get_attribute("href")
        except WebDriverException as e:
            self.logger.debug(attribute_scraping_failure(
                f"download link for '{product_url}'"))
            return {}

        # scrape version
        try:
            version_string = product_div.find_element(
                by=By.CSS_SELECTOR, value=CSS_SELECTOR_SOFTWARE_VERSION
            ).get_attribute("innerHTML")
            version = version_string.split("Version ")[1][:-1]
        except Exception as e:
            self.logger.debug(attribute_scraping_failure(
                f"version for '{product_url}'"))

        self.logger.info(firmware_scraping_success(
            f"of {product_name} {product_url}"))
        return {
            "manufacturer": self.name,
            "product_name": product_name,
            "product_type": category_name_clean,
            "version": version,
            "release_date": None,
            "checksum_scraped": None,
            "download_link": download_link,
            "additional_data": {},
        }

    def _scrape_product_ids(self) -> list:
        CSS_SELECTOR_PRODUCT_CATEGORY_NAME_ROOT = "body > div.middle.responsiveHeader.cf > section > div.par.parsys > div.sdx-container.section > sdx-tabs > div"
        CSS_SELECTOR_IDS = ".tab-link"

        # this mapping is used as a fallback in case a clean category name cannot be scraped
        product_category_map = {
            "internetrouter": "Internet router",
            "heimvernetzung": "Home networking accessories",
            "festnetz": "Fixed-network telephony",
            "bluetv": "Swisscom blue tv",
        }

        try:
            product_categories = self.driver.find_element(
                by=By.CSS_SELECTOR, value=CSS_SELECTOR_PRODUCT_CATEGORY_NAME_ROOT
            ).find_elements(by=By.CSS_SELECTOR, value=CSS_SELECTOR_IDS)

            product_ids = []
            for category in product_categories:
                category_name = category.get_attribute("data-panel")

                css_selector_product_category_name_clean_root = f"body > div.middle.responsiveHeader.cf > section > div.par.parsys > div > div[data-id='{category_name}']"
                category_name_clean_root = self.driver.find_element(
                    by=By.CSS_SELECTOR, value=css_selector_product_category_name_clean_root
                )
                category_name_clean = category_name_clean_root.find_element(
                    by=By.CSS_SELECTOR, value=f"h2").text
                if not category_name_clean and category_name in product_category_map:
                    category_name_clean = product_category_map[category_name]

                products = self.driver.find_element(
                    by=By.CSS_SELECTOR, value=f"div[data-id='{category_name}']"
                ).find_elements(by=By.CSS_SELECTOR, value=CSS_SELECTOR_IDS)

                for product in products:
                    product_id = product.get_attribute("data-panel")
                    product_ids.append(
                        (category_name, category_name_clean, product_id))
            return product_ids

        except WebDriverException as e:
            self.logger.error(f"Could not scrape product names.\n{e}")
            self.logger.important(abort_scraping())
            return []

    def scrape_metadata(self) -> list[dict]:
        CSS_SELECTOR_ACCEPT_COOKIES = "body > div.sdx-container > div.modal.modal--open > div > div > div.modal__body > div.button-group.button-group--responsive > button.button.button--responsive.button--primary"

        self.logger.important(start_scraping())
        try:
            self.driver.get(self.scrape_entry_url)
            self.logger.info(entry_point_url_success(self.scrape_entry_url))
        except WebDriverException as e:
            self.logger.error(entry_point_url_failure(self.scrape_entry_url))
            self.logger.important(abort_scraping())
            return []

        # when first accessing the website, cookies must be accepted
        try:
            self.driver.find_element(
                by=By.CSS_SELECTOR, value=CSS_SELECTOR_ACCEPT_COOKIES).click()
        except WebDriverException as e:
            pass

        product_ids = self._scrape_product_ids()
        extracted_data = []
        for (cat_name, cat_name_clean, prod_id) in product_ids:
            if metadata := self._scrape_product_metadata(cat_name, cat_name_clean, prod_id):
                extracted_data.append(metadata)

        self.logger.important(finish_scraping())
        return extracted_data


if __name__ == "__main__":
    logger = get_logger()

    scraper = SwisscomScraper(logger, DOWNLOAD_URL_EN, headless=False)

    firmware_data = scraper.scrape_metadata()
    with open("scraped_metadata/firmware_data_swisscom.json", "w") as firmware_file:
        json.dump(firmware_data, firmware_file)
