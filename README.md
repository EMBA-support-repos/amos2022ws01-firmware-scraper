# Firmware Scraper (AMOS SS 2022)
[![Pytest Suite](https://github.com/amosproj/amos2022ws01-firmware-scraper/actions/workflows/pytest.yml/badge.svg)](https://github.com/amosproj/amos2022ws01-firmware-scraper/actions/workflows/pytest.yml)


![Logo of the project](https://github.com/amosproj/amos2022ws01-firmware-scraper/blob/main/documentation/logos/team-logo-black-1000.png#gh-light-mode-only) 
![Logo of the project](https://github.com/amosproj/amos2022ws01-firmware-scraper/blob/main/documentation/logos/team-logo-white-1000.png#gh-dark-mode-only)

## TLDR;

This [Selenium-based](https://github.com/SeleniumHQ/selenium) firmware scraper gathers firmware data from 18 vendors. Our automated solution scrapes metadata and downloads corresponding firmwares. The results can be used for InfoSec research.

## Installation
## Option 1: On your local machine (Ubuntu only)

```shell
git clone https://github.com/amosproj/amos2022ws01-firmware-scraper
# or download and unpack .zip amos2022ws01-firmware-scraper
cd amos2022ws01-firmware-scraper
./install.sh
source .venv/bin/activate

# Make sure MySQL server is running
sudo systemctl start mysql.service

export MYSQL_USER=<your username>
export MYSQL_PASSWORD=<your password>
export LOG_LEVEL=DEBUG

# Start the scraper:
python -m src.core
```

## Option 2: Docker 
**Requirements**: Docker should be installed on your machine.

```shell
git clone https://github.com/amosproj/amos2022ws01-firmware-scraper
#or download and unpack .zip amos2022ws01-firmware-scraper
cd amos2022ws01-firmware-scraper
docker-compose up --build
```

