from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from src.db.session import get_db
from src.db.models import NewsArticle
from src.api.v1.dependencies import get_current_user
from src.api.v1.news.schemas import PromptRequest, NewsSummaryRequestSchema
from src.api.v1.news.service import NewsService


def get_news_service(db: Session = Depends(get_db)) -> NewsService:
    """依賴注入 NewsService 實例，注入 db session"""
    from src.main import news_service
    news_service.db = db
    return news_service


router = APIRouter(prefix="/news", tags=["news"])


@router.get("/")
async def get_news_articles(service: NewsService = Depends(get_news_service)):
    """獲取所有新聞"""
    articles = service.db.query(NewsArticle).order_by(NewsArticle.time.desc()).all()
    result = []
    for article in articles:
        upvotes_count, is_upvoted = service.get_article_upvote_details(article.id, None)
        result.append({
            "id": article.id,
            "url": article.url,
            "title": article.title,
            "time": article.time,
            "content": article.content,
            "summary": article.summary,
            "reason": article.reason,
            "upvotes": upvotes_count,
            "is_upvoted": is_upvoted
        })
    return result


@router.get("/user_news")
async def read_user_news(user=Depends(get_current_user), service: NewsService = Depends(get_news_service)):
    """獲取當前用戶的新聞"""
    articles = service.db.query(NewsArticle).order_by(NewsArticle.time.desc()).all()
    result = []
    for article in articles:
        upvotes, upvoted = service.get_article_upvote_details(article.id, user.id)
        result.append({
            "id": article.id,
            "url": article.url,
            "title": article.title,
            "time": article.time,
            "content": article.content,
            "summary": article.summary,
            "reason": article.reason,
            "upvotes": upvotes,
            "is_upvoted": upvoted
        })
    return result


@router.post("/search_news")
async def search_news(request: PromptRequest, service: NewsService = Depends(get_news_service)):
    """搜尋新聞"""
    return service.search_news(request.prompt)


@router.post("/news_summary")
async def news_summary(payload: NewsSummaryRequestSchema, u=Depends(get_current_user), service: NewsService = Depends(get_news_service)):
    """生成新聞摘要"""
    return service.news_summary(payload.content)


@router.post("/{news_id}/upvote")
async def upvote_news(news_id: int, user=Depends(get_current_user), service: NewsService = Depends(get_news_service)):
    """點贊新聞"""
    message = service.toggle_upvote(news_id, user.id)
    return {"message": message}