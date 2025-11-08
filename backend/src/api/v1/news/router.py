from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from src.db.session import get_db
from src.db.models import NewsArticle
from src.api.v1.dependencies import get_current_user
from src.api.v1.news.schemas import PromptRequest, NewsSummaryRequestSchema
from src.api.v1.news.service import NewsService

router = APIRouter(prefix="/news", tags=["news"])
news_service = NewsService()


@router.get("/")
async def get_news_articles(db: Session = Depends(get_db)):
    """獲取所有新聞"""
    articles = db.query(NewsArticle).order_by(NewsArticle.time.desc()).all()
    result = []
    for article in articles:
        upvotes_count, is_upvoted = news_service.get_article_upvote_details(db, article.id, None)
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
async def read_user_news(db: Session = Depends(get_db), user=Depends(get_current_user)):
    """獲取當前用戶的新聞"""
    articles = db.query(NewsArticle).order_by(NewsArticle.time.desc()).all()
    result = []
    for article in articles:
        upvotes, upvoted = news_service.get_article_upvote_details(db, article.id, user.id)
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
async def search_news(request: PromptRequest):
    """搜尋新聞"""
    return news_service.search_news(request.prompt)


@router.post("/news_summary")
async def news_summary(payload: NewsSummaryRequestSchema, u=Depends(get_current_user)):
    """生成新聞摘要"""
    return news_service.news_summary(payload.content)


@router.post("/{news_id}/upvote")
async def upvote_news(news_id: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    """點讚新聞"""
    message = news_service.toggle_upvote(db, news_id, user.id)
    return {"message": message}