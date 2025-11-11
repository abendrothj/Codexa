"""
Example: Simple web scraper using requests and BeautifulSoup.

This module demonstrates how to scrape data from websites.
"""

import requests
from bs4 import BeautifulSoup
from typing import List, Dict, Optional


class WebScraper:
    """A simple web scraper for extracting data from HTML pages."""

    def __init__(self, base_url: str) -> None:
        """
        Initialize the web scraper.

        Args:
            base_url: The base URL to scrape
        """
        self.base_url = base_url
        self.session = requests.Session()

    def fetch_page(self, url: str) -> Optional[str]:
        """
        Fetch HTML content from a URL.

        Args:
            url: The URL to fetch

        Returns:
            HTML content as string, or None if fetch fails
        """
        try:
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            return response.text
        except requests.RequestException as e:
            print(f"Error fetching {url}: {e}")
            return None

    def parse_articles(self, html: str) -> List[Dict[str, str]]:
        """
        Parse articles from HTML content.

        Args:
            html: HTML content to parse

        Returns:
            List of article dictionaries with title and link
        """
        soup = BeautifulSoup(html, "html.parser")
        articles = []

        for article in soup.find_all("article"):
            title_tag = article.find("h2")
            link_tag = article.find("a")

            if title_tag and link_tag:
                articles.append(
                    {
                        "title": title_tag.get_text(strip=True),
                        "link": link_tag.get("href", ""),
                    }
                )

        return articles

    def scrape(self) -> List[Dict[str, str]]:
        """
        Scrape articles from the base URL.

        Returns:
            List of scraped articles
        """
        html = self.fetch_page(self.base_url)
        if html:
            return self.parse_articles(html)
        return []


def main() -> None:
    """Main function to run the scraper."""
    scraper = WebScraper("https://example.com/blog")
    articles = scraper.scrape()

    print(f"Found {len(articles)} articles:")
    for article in articles:
        print(f"- {article['title']}: {article['link']}")


if __name__ == "__main__":
    main()
