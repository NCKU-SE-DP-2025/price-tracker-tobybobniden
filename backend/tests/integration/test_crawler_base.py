"""Unit tests for NewsCrawlerBase and its implementations"""
import unittest
from unittest.mock import MagicMock, patch
from pydantic import AnyHttpUrl
from src.crawler.base import NewsCrawlerBase, News, Headline
from src.crawler.exceptions import DomainMismatchException


class MockNewsCrawler(NewsCrawlerBase):
    """Mock crawler for testing NewsCrawlerBase functionality"""
    
    news_website_url = "https://www.example.com"
    news_website_news_child_urls = ["https://news.example.com"]

    def get_headline(self, search_term: str, page: int | tuple[int, int]):
        """Mock implementation of get_headline"""
        return [Headline(title="Test Article", url="https://www.example.com/article")]

    def parse(self, url: AnyHttpUrl | str):
        """Mock implementation of parse"""
        return News(
            title="Test Article",
            url=url,
            time="2023-09-08T00:00:00",
            content="This is the content of the article."
        )

    @staticmethod
    def save(news: News, db=None):
        """Mock implementation of save"""
        return True


class TestNewsCrawlerBase(unittest.TestCase):
    """Test cases for NewsCrawlerBase"""

    def setUp(self):
        """Set up test fixtures"""
        self.crawler = MockNewsCrawler()

    def test_is_valid_url_valid(self):
        """Test that valid URLs are recognized"""
        valid_url = "https://www.example.com/article"
        self.assertTrue(self.crawler._is_valid_url(valid_url))

    def test_is_valid_url_invalid(self):
        """Test that invalid URLs are rejected"""
        invalid_url = "https://www.invalid.com/article"
        self.assertFalse(self.crawler._is_valid_url(invalid_url))

    def test_is_valid_url_child(self):
        """Test that child domain URLs are recognized"""
        valid_child_url = "https://news.example.com/article"
        self.assertTrue(self.crawler._is_valid_url(valid_child_url))

    def test_is_valid_url_raises_domain_mismatch(self):
        """Test that validate_and_parse raises exception for invalid domains"""
        invalid_url = "https://www.invalid.com/article"

        with self.assertRaises(DomainMismatchException):
            self.crawler.validate_and_parse(invalid_url)

    def test_validate_and_parse_valid(self):
        """Test that validate_and_parse works for valid URLs"""
        valid_url = "https://www.example.com/article"
        news = self.crawler.validate_and_parse(valid_url)
        
        self.assertEqual(news.title, "Test Article")
        self.assertEqual(str(news.url), valid_url)
        self.assertEqual(news.time, "2023-09-08T00:00:00")
        self.assertEqual(news.content, "This is the content of the article.")

    def test_get_headline(self):
        """Test get_headline returns correct data"""
        headlines = self.crawler.get_headline(search_term="test", page=1)
        
        self.assertEqual(len(headlines), 1)
        self.assertEqual(headlines[0].title, "Test Article")
        self.assertEqual(str(headlines[0].url), "https://www.example.com/article")

    def test_parse(self):
        """Test parse returns correct News object"""
        news = self.crawler.parse("https://www.example.com/article")
        
        self.assertEqual(news.title, "Test Article")
        self.assertEqual(str(news.url), "https://www.example.com/article")
        self.assertEqual(news.time, "2023-09-08T00:00:00")
        self.assertEqual(news.content, "This is the content of the article.")

    def test_save(self):
        """Test save method"""
        news = News(
            title="Test Article",
            url="https://www.example.com/article",
            time="2023-09-08T00:00:00",
            content="This is the content of the article."
        )
        result = self.crawler.save(news)
        self.assertTrue(result)

    def test_get_domain(self):
        """Test domain extraction from URLs"""
        url1 = "https://www.example.com/article/123"
        url2 = "https://news.example.com/article/456"
        
        domain1 = self.crawler._get_domain(url1)
        domain2 = self.crawler._get_domain(url2)
        
        self.assertEqual(domain1, "https://www.example.com")
        self.assertEqual(domain2, "https://news.example.com")

    def test_headline_model(self):
        """Test Headline pydantic model"""
        headline = Headline(
            title="Breaking News",
            url="https://www.example.com/news/123"
        )
        self.assertEqual(headline.title, "Breaking News")
        self.assertEqual(str(headline.url), "https://www.example.com/news/123")

    def test_news_model(self):
        """Test News pydantic model"""
        news = News(
            title="Article Title",
            url="https://www.example.com/article",
            time="2023-09-08",
            content="Article content here",
            summary="Summary",
            reason="Reason"
        )
        self.assertEqual(news.title, "Article Title")
        self.assertEqual(news.summary, "Summary")
        self.assertEqual(news.reason, "Reason")


if __name__ == '__main__':
    unittest.main()
