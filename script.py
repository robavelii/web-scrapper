import asyncio
import aiohttp
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from urllib import robotparser
import csv
import time
import random
from fake_useragent import UserAgent
import logging
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AdvancedScraper:
    def __init__(self, start_url, max_pages=10, use_selenium=False):
        self.start_url = start_url
        self.max_pages = max_pages
        self.domain = urlparse(start_url).netloc
        self.scraped_urls = set()
        self.to_scrape = [start_url]
        self.user_agent = UserAgent()
        self.use_selenium = use_selenium
        self.session = None
        self.driver = None
        self.robots = None

    async def init_session(self):
        self.session = aiohttp.ClientSession(headers={'User-Agent': self.user_agent.random})

    def init_selenium(self):
        options = Options()
        options.add_argument("--headless")
        options.add_argument(f"user-agent={self.user_agent.random}")
        self.driver = webdriver.Chrome(options=options)

    async def fetch_robots_txt(self):
        robots_url = f"https://{self.domain}/robots.txt"
        self.robots = robotparser.RobotFileParser(robots_url)
        async with self.session.get(robots_url) as response:
            if response.status == 200:
                content = await response.text()
                self.robots.parse(content.splitlines())
            else:
                logger.warning(f"No robots.txt found at {robots_url}")

    async def is_allowed(self, url):
        if self.robots:
            return self.robots.can_fetch(self.user_agent.random, url)
        return True

    async def fetch_page(self, url):
        if not await self.is_allowed(url):
            logger.info(f"Skipping {url} as per robots.txt")
            return None

        if self.use_selenium:
            return await self.fetch_with_selenium(url)
        else:
            return await self.fetch_with_requests(url)

    async def fetch_with_requests(self, url):
        try:
            async with self.session.get(url) as response:
                if response.status == 200:
                    return await response.text()
                else:
                    logger.warning(f"Failed to fetch {url}: HTTP {response.status}")
        except Exception as e:
            logger.error(f"Error fetching {url}: {str(e)}")
        return None

    async def fetch_with_selenium(self, url):
        try:
            self.driver.get(url)
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            return self.driver.page_source
        except Exception as e:
            logger.error(f"Error fetching {url} with Selenium: {str(e)}")
        return None

    def parse_page(self, html, url):
        soup = BeautifulSoup(html, 'html.parser')
        title = soup.title.string if soup.title else ''
        description = soup.find('meta', attrs={'name': 'description'})
        description = description['content'] if description else ''
        links = [urljoin(url, a['href']) for a in soup.find_all('a', href=True)]
        return {
            'url': url,
            'title': title,
            'description': description,
            'links': links
        }

    async def scrape_website(self):
        await self.init_session()
        if self.use_selenium:
            self.init_selenium()
        await self.fetch_robots_txt()

        scraped_data = []
        while self.to_scrape and len(scraped_data) < self.max_pages:
            url = self.to_scrape.pop(0)
            if url in self.scraped_urls:
                continue

            logger.info(f"Scraping: {url}")
            html = await self.fetch_page(url)
            if html:
                data = self.parse_page(html, url)
                scraped_data.append(data)
                self.scraped_urls.add(url)

                new_links = [link for link in data['links']
                             if link not in self.scraped_urls and urlparse(link).netloc == self.domain]
                self.to_scrape.extend(new_links)

            await asyncio.sleep(random.uniform(1, 3))

        await self.session.close()
        if self.driver:
            self.driver.quit()

        return scraped_data

def save_to_csv(data, filename='scraped_data.csv'):
    if not data:
        logger.warning("No data to save.")
        return

    keys = data[0].keys()
    with open(filename, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=keys)
        writer.writeheader()
        for row in data:
            writer.writerow(row)

async def main():
    start_url = input("Enter the URL to start scraping: ")
    max_pages = int(input("Enter the maximum number of pages to scrape: "))
    use_selenium = input("Use Selenium for JavaScript rendering? (y/n): ").lower() == 'y'

    scraper = AdvancedScraper(start_url, max_pages, use_selenium)
    scraped_data = await scraper.scrape_website()
    save_to_csv(scraped_data)
    logger.info(f"Scraped {len(scraped_data)} pages. Data saved to scraped_data.csv")

if __name__ == '__main__':
    asyncio.run(main())