from src.api.v1.news.router import router
from src.api.v1.news.service import NewsService
from src.api.v1.news.schemas import PromptRequest, NewsSummaryRequestSchema

__all__ = [
    "router",
    "NewsService",
    "PromptRequest",
    "NewsSummaryRequestSchema",
]