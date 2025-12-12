"""Core tests for UDNCrawler (API and parsing functionality)"""
import unittest
from unittest.mock import patch, MagicMock
from src.crawler.udn_crawler import UDNCrawler
from src.crawler.base import Headline, News
from src.crawler.exceptions import DomainMismatchException


class TestUDNCrawlerCore(unittest.TestCase):
    """Test suite for UDNCrawler core functionality"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.scraper = UDNCrawler(timeout=5)
    
    # ==================== Tests for _perform_request ====================
    
    @patch("src.crawler.udn_crawler.requests.get")
    def test_perform_request_success(self, mock_get):
        """Test successful HTTP request"""
        mock_response = MagicMock()
        mock_response.json.return_value = {"lists": []}
        mock_get.return_value = mock_response
        
        params = {"page": 1, "id": "search:test"}
        response = self.scraper._perform_request(params)
        
        self.assertEqual(response, mock_response)
        mock_get.assert_called_once_with(
            "https://udn.com/api/more",
            params=params,
            timeout=5
        )
    
    @patch("src.crawler.udn_crawler.requests.get")
    def test_perform_request_failure(self, mock_get):
        """Test failed HTTP request"""
        mock_get.side_effect = Exception("Network error")
        
        params = {"page": 1, "id": "search:test"}
        
        with self.assertRaises(Exception):
            self.scraper._perform_request(params)
    
    # ==================== Tests for _create_search_params ====================
    
    def test_create_search_params(self):
        """Test search parameters creation"""
        params = self.scraper._create_search_params(1, "價格")
        
        self.assertEqual(params["page"], 1)
        self.assertEqual(params["channelId"], 2)
        self.assertEqual(params["type"], "searchword")
        self.assertIn("search:", params["id"])
        # URL encoding check
        self.assertIn("%E5%83%B9%E6%A0%BC", params["id"])
    
    # ==================== Tests for _fetch_news ====================
    
    @patch("src.crawler.udn_crawler.requests.get")
    def test_fetch_news_success(self, mock_get):
        """Test successful news fetching"""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "lists": [
                {
                    "title": "Test News 1",
                    "titleLink": "https://news.udn.com/news/1"
                },
                {
                    "title": "Test News 2",
                    "titleLink": "https://news.udn.com/news/2"
                }
            ]
        }
        mock_get.return_value = mock_response
        
        headlines = self.scraper._fetch_news(1, "test")
        
        self.assertEqual(len(headlines), 2)
        self.assertEqual(headlines[0].title, "Test News 1")
        self.assertEqual(headlines[1].title, "Test News 2")
    
    @patch("src.crawler.udn_crawler.requests.get")
    def test_fetch_news_empty_result(self, mock_get):
        """Test news fetching with empty results"""
        mock_response = MagicMock()
        mock_response.json.return_value = {"lists": []}
        mock_get.return_value = mock_response
        
        headlines = self.scraper._fetch_news(1, "test")
        
        self.assertEqual(len(headlines), 0)
    
    # ==================== Tests for get_headline ====================
    
    @patch.object(UDNCrawler, "_fetch_news")
    def test_get_headline_single_page(self, mock_fetch):
        """Test getting headlines from single page"""
        mock_fetch.return_value = [
            Headline(title="News 1", url="https://news.udn.com/1"),
            Headline(title="News 2", url="https://news.udn.com/2")
        ]
        
        headlines = self.scraper.get_headline("test", 1)
        
        self.assertEqual(len(headlines), 2)
        mock_fetch.assert_called_once_with(1, "test")
    
    @patch.object(UDNCrawler, "_fetch_news")
    def test_get_headline_multiple_pages(self, mock_fetch):
        """Test getting headlines from multiple pages"""
        mock_fetch.side_effect = [
            [Headline(title="Page 1 News", url="https://news.udn.com/1")],
            [Headline(title="Page 2 News", url="https://news.udn.com/2")]
        ]
        
        headlines = self.scraper.get_headline("test", (1, 2))
        
        self.assertEqual(len(headlines), 2)
        self.assertEqual(mock_fetch.call_count, 2)
    
    # ==================== Tests for parse ====================
    
    @patch("src.crawler.udn_crawler.requests.get")
    def test_parse_article(self, mock_get):
        """Test article parsing with valid HTML"""
        mock_response = MagicMock()
        mock_response.text = """
        <html>
            <h1 class="article-content__title">Test Article Title</h1>
            <time class="article-content__time">2024-01-01 10:00</time>
            <section class="article-content__editor">
                <p>Paragraph 1</p>
                <p>Paragraph 2</p>
            </section>
        </html>
        """
        mock_get.return_value = mock_response
        
        news = self.scraper.parse("https://news.udn.com/news/1")
        
        self.assertEqual(news.title, "Test Article Title")
        self.assertEqual(news.time, "2024-01-01 10:00")
        self.assertIn("Paragraph 1", news.content)
        self.assertIn("Paragraph 2", news.content)
    
    @patch("src.crawler.udn_crawler.requests.get")
    def test_parse_article_with_missing_elements(self, mock_get):
        """Test article parsing with missing HTML elements"""
        mock_response = MagicMock()
        mock_response.text = """
        <html>
            <h1 class="article-content__title">Test Title</h1>
        </html>
        """
        mock_get.return_value = mock_response
        
        news = self.scraper.parse("https://news.udn.com/news/1")
        
        self.assertEqual(news.title, "Test Title")
        self.assertEqual(news.time, "")
        self.assertEqual(news.content, "")
    
    def test_parse_invalid_domain(self):
        """Test parsing with invalid domain URL"""
        with self.assertRaises(DomainMismatchException):
            self.scraper.parse("https://google.com/article")
    
    # ==================== Tests for _is_valid_url ====================
    
    def test_is_valid_url_udn_news(self):
        """Test URL validation for UDN news domain"""
        is_valid = self.scraper._is_valid_url("https://news.udn.com/news/123")
        self.assertTrue(is_valid)
    
    def test_is_valid_url_invalid_domain(self):
        """Test URL validation for non-UDN domain"""
        is_valid = self.scraper._is_valid_url("https://google.com/news")
        self.assertFalse(is_valid)


if __name__ == "__main__":
    unittest.main()
