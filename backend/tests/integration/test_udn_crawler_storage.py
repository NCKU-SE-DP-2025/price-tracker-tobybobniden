"""Storage tests for UDNCrawler (database operations)"""
import unittest
from unittest.mock import patch, MagicMock
from src.crawler.udn_crawler import UDNCrawler
from src.crawler.base import News


class TestUDNCrawlerStorage(unittest.TestCase):
    """Test suite for UDNCrawler storage functionality"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.scraper = UDNCrawler(timeout=5)
    
    # ==================== Tests for save ====================
    
    @patch("src.crawler.udn_crawler.Session")
    def test_save_news(self, mock_session_class):
        """Test saving news to database"""
        mock_db = MagicMock()
        news = News(
            title="Test Article",
            url="https://news.udn.com/1",
            time="2024-01-01",
            content="Test content"
        )
        
        result = self.scraper.save(news, mock_db)
        
        self.assertTrue(result)
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()
    
    def test_save_without_database(self):
        """Test saving without database session"""
        news = News(
            title="Test Article",
            url="https://news.udn.com/1",
            time="2024-01-01",
            content="Test content"
        )
        
        result = self.scraper.save(news, None)
        
        self.assertFalse(result)
    
    def test_save_handles_database_error(self):
        """Test saving with database error handling"""
        mock_db = MagicMock()
        mock_db.add.side_effect = Exception("Database error")
        
        news = News(
            title="Test Article",
            url="https://news.udn.com/1",
            time="2024-01-01",
            content="Test content"
        )
        
        result = self.scraper.save(news, mock_db)
        
        self.assertFalse(result)
        mock_db.rollback.assert_called_once()


if __name__ == "__main__":
    unittest.main()
