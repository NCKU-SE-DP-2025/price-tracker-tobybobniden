"""Base crawler class with OOP design"""
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, AnyHttpUrl
from urllib.parse import urlparse
from src.crawler.exceptions import DomainMismatchException


class Headline(BaseModel):
    """Headline data model"""
    title: str
    url: AnyHttpUrl


class News(BaseModel):
    """News article data model"""
    title: str
    url: AnyHttpUrl
    time: str
    content: str
    summary: Optional[str] = None
    reason: Optional[str] = None


class NewsCrawlerBase(ABC):
    """Base class for news crawlers with domain validation"""
    
    # These should be overridden by subclasses
    news_website_url: str = None
    news_website_news_child_urls: list[str] = []
    
    def _get_domain(self, url: str) -> str:
        """Extract domain from URL"""
        parsed = urlparse(str(url))
        return f"{parsed.scheme}://{parsed.netloc}"
    
    def _is_valid_url(self, url: AnyHttpUrl | str) -> bool:
        """Check if URL belongs to the crawler's website domain"""
        url_str = str(url)
        base_domain = self._get_domain(self.news_website_url)
        url_domain = self._get_domain(url_str)
        
        # Check if URL belongs to main website or child URLs
        if url_domain == base_domain:
            return True
        
        for child_url in self.news_website_news_child_urls:
            child_domain = self._get_domain(child_url)
            if url_domain == child_domain:
                return True
        
        return False
    
    def validate_and_parse(self, url: AnyHttpUrl | str) -> News:
        """Validate URL domain and parse the news article"""
        if not self._is_valid_url(url):
            raise DomainMismatchException(
                f"URL domain does not match crawler's website domain. URL: {url}"
            )
        return self.parse(url)
    
    @abstractmethod
    def get_headline(self, search_term: str, page: int | tuple[int, int]) -> list[Headline]:
        """Get headlines for a search term and page number
        
        Args:
            search_term: Search keyword
            page: Page number or tuple of (start_page, end_page)
            
        Returns:
            List of headlines
        """
        pass
    
    @abstractmethod
    def parse(self, url: AnyHttpUrl | str) -> News:
        """Parse full article content from URL
        
        Args:
            url: Article URL
            
        Returns:
            News object with full content
        """
        pass
    
    @staticmethod
    @abstractmethod
    def save(news: News, db=None) -> bool:
        """Save news article to database
        
        Args:
            news: News object to save
            db: Database session
            
        Returns:
            True if saved successfully
        """
        pass
