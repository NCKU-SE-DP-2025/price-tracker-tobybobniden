"""UDN News Crawler implementation"""
import requests
from bs4 import BeautifulSoup
from urllib.parse import quote
from pydantic import AnyHttpUrl
from src.crawler.base import NewsCrawlerBase, News, Headline
from src.crawler.exceptions import DomainMismatchException
from src.db.models import NewsArticle
from sqlalchemy.orm import Session


class UDNCrawler(NewsCrawlerBase):
    """Crawler for UDN (聯合新聞網) news articles"""
    
    news_website_url = "https://udn.com"
    news_website_news_child_urls = ["https://news.udn.com"]
    
    def __init__(self, timeout: int = 10):
        """Initialize UDNCrawler with timeout configuration
        
        Args:
            timeout: Request timeout in seconds (default: 10)
        """
        self.timeout = timeout
    
    def _perform_request(self, params: dict):
        """Perform HTTP request to UDN API
        
        Args:
            params: Query parameters for the API
            
        Returns:
            Response object from requests library
            
        Raises:
            Exception: If request fails
        """
        try:
            response = requests.get("https://udn.com/api/more", params=params, timeout=self.timeout)
            response.raise_for_status()
            return response
        except Exception as e:
            print(f"Error performing request: {e}")
            raise
    
    def _create_search_params(self, page: int, search_term: str) -> dict:
        """Create search parameters for UDN API
        
        Args:
            page: Page number
            search_term: Search keyword
            
        Returns:
            Dictionary of query parameters
        """
        return {
            "page": page,
            "id": f"search:{quote(search_term)}",
            "channelId": 2,
            "type": "searchword",
        }
    
    def _fetch_news(self, page: int, search_term: str) -> list[Headline]:
        """Fetch news headlines from UDN API
        
        Args:
            page: Page number
            search_term: Search keyword
            
        Returns:
            List of Headline objects
        """
        params = self._create_search_params(page, search_term)
        response = self._perform_request(params)
        data = response.json()
        
        headlines = []
        for item in data.get("lists", []):
            headline = Headline(
                title=item.get("title", ""),
                url=item.get("titleLink", "")
            )
            headlines.append(headline)
        
        return headlines
    
    def get_headline(self, search_term: str, page: int | tuple[int, int]) -> list[Headline]:
        """Get headlines from UDN news API
        
        Args:
            search_term: Search keyword (e.g., "價格")
            page: Page number or tuple of (start_page, end_page)
            
        Returns:
            List of headlines with title and URL
        """
        headlines = []
        
        # Handle page parameter
        if isinstance(page, tuple):
            pages = range(page[0], page[1] + 1)
        else:
            pages = [page]
        
        for page_num in pages:
            try:
                page_headlines = self._fetch_news(page_num, search_term)
                headlines.extend(page_headlines)
            except Exception as e:
                print(f"Error fetching headlines from page {page_num}: {e}")
                continue
        
        return headlines
    
    def _is_valid_url(self, url: str) -> bool:
        """Check if URL belongs to UDN website
        
        Args:
            url: URL to validate
            
        Returns:
            True if URL is from UDN, False otherwise
        """
        return super()._is_valid_url(url)
    
    def parse(self, url: AnyHttpUrl | str) -> News:
        """Parse full article content from UDN URL
        
        Args:
            url: Article URL from UDN
            
        Returns:
            News object with title, time, content, and URL
            
        Raises:
            DomainMismatchException: If URL is not from UDN
        """
        # Validate domain first
        if not self._is_valid_url(str(url)):
            raise DomainMismatchException(
                f"URL domain does not match UDN website. URL: {url}"
            )
        
        try:
            response = requests.get(str(url), timeout=10)
            soup = BeautifulSoup(response.text, "html.parser")
            
            # Extract article title
            title_elem = soup.find("h1", class_="article-content__title")
            title = title_elem.text if title_elem else "Unknown Title"
            
            # Extract article time
            time_elem = soup.find("time", class_="article-content__time")
            time = time_elem.text if time_elem else ""
            
            # Extract article content
            content_section = soup.find("section", class_="article-content__editor")
            paragraphs = []
            
            if content_section:
                for p in content_section.find_all("p"):
                    text = p.text.strip()
                    if text and "▪" not in text:
                        paragraphs.append(text)
            
            content = " ".join(paragraphs)
            
            return News(
                title=title,
                url=url,
                time=time,
                content=content
            )
        except DomainMismatchException:
            raise
        except Exception as e:
            print(f"Error parsing article from {url}: {e}")
            raise
    
    @staticmethod
    def save(news: News, db: Session = None) -> bool:
        """Save news article to database
        
        Args:
            news: News object to save
            db: SQLAlchemy database session
            
        Returns:
            True if saved successfully, False otherwise
        """
        if not db:
            return False
        
        try:
            article = NewsArticle(
                url=str(news.url),
                title=news.title,
                time=news.time,
                content=news.content,
                summary=news.summary or "",
                reason=news.reason or ""
            )
            db.add(article)
            db.commit()
            return True
        except Exception as e:
            print(f"Error saving article to database: {e}")
            db.rollback()
            return False
