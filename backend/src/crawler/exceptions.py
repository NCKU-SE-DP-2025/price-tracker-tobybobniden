"""Crawler related exceptions"""


class CrawlerException(Exception):
    """Base exception for crawler operations"""
    pass


class DomainMismatchException(CrawlerException):
    """Raised when URL domain doesn't match the crawler's website domain"""
    pass
