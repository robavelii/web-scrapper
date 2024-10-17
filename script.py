import requests
from bs4 import BeautifulSoup
import csv 
from urllib.parse import urljoin, urlparse
import time
import random


def get_domain(url):
    return urlparse(url).netloc

def extract_text(element):
    return element.get_text(strip=True) if element else ""

def scrape_page(url):
    try: 
        response = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'})
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')

        # Extract title
        title = extract_text(soup.title) or extract_text(soup.find('h1'))
        
        # Extract description
        description = extract_text(soup.find('meta', attrs={'name': 'description'}))
        if not description:
            description = extract_text(soup.find('p'))

        # Extract keywords
        keywords = extract_text(soup.find('meta', attrs={'name': 'keywords'}))

        # Extract author
        author = extract_text(soup.find('meta', attrs={'name': 'author'}))

          
        # Extract links
        links = [urljoin(url, a.get('href')) for a in soup.find_all('a', href=True)]
        internal_links = [link for link in links if get_domain(link) == get_domain(url)]
        external_links = [link for link in links if get_domain(link) != get_domain(url)]

        return {
            'url': url,
            'title': title,
            'description': description,
            'keywords': keywords,
            'author': author,
            'internal_links': internal_links,
            'external_links': external_links
        }

    except requests.RequestException as e:
        print(f"Error fetching {url}: {e}")
        return None
    
def scrape_website(start_url, max_pages=10):
    domain = get_domain(start_url)
    scraped_data = []
    to_scrape = [start_url]
    scraped_urls = set()

    while to_scrape and len(scraped_data) < max_pages:
        url = to_scrape.pop(0)
        if url in scraped_urls:
            continue

        print(f"Scraping {url}")
        data = scrape_page(url)

        if data:
            scraped_data.append(data)
            scraped_urls.add(url)

            # Add new internal links to scraped
            new_links = [link for link in data['internal_links'] 
                         if link not in scraped_urls and get_domain(link) == domain]
            to_scrape.extend(new_links)

        time.sleep(random.uniform(1, 3)) # Add delay between requests

    return scraped_data

def save_to_csv(data, filename = 'scraped_data.csv'):
    if not data: 
        print("No data to save")
        return
    
    keys = data[0].keys()
    with open(filename, 'w', newline='', encoding='utf-8') as output_file:
        writer = csv.DictWriter(output_file, fieldnames=keys)
        writer.writeheader()
        for row in data:
            writer.writerow({k: str(v) if isinstance(v,list) else v for k, v in row.items()})

def main():
    start_url = input("Enter the URL to start scrapping: ")
    max_pages = int(input("Enter the maximum number of pages to scrape: "))

    scraped_data = scrape_website(start_url, max_pages)
    save_to_csv(scraped_data)
    print(f"Scraped {len(scraped_data)} pages. Data saved to scraped_data.csv")
    

if __name__ == '__main__':
    main()