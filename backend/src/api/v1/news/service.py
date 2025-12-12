import requests
from typing import List, Optional, Union
from sqlalchemy.orm import Session
from sqlalchemy import delete, insert, select
from src.db.models import NewsArticle, user_news_association_table
from src.db.session import SessionLocal
from src.api.v1.ai.service import AIService 
from src.crawler.udn_crawler import UDNCrawler
from src.crawler.base import News


class NewsService:
    """將新聞抓取、處理、儲存與搜尋等邏輯包裝"""

    def __init__(self, ai_service: AIService): 
        self.ai_service = ai_service
        self.crawler = UDNCrawler()

    def add_news_article(self, db: Session, news_data: News) -> NewsArticle:
        article = NewsArticle(
            url=str(news_data.url),
            title=news_data.title,
            time=news_data.time,
            content=news_data.content,
            summary=news_data.summary or "",
            reason=news_data.reason or "",
        )
        db.add(article)
        db.commit()
        db.refresh(article)
        return article

    def get_article_upvote_details(self, db: Session, article_id: int, user_id: int = None):
        count = db.query(user_news_association_table).filter_by(news_articles_id=article_id).count()
        voted = False
        if user_id:
            voted = db.query(user_news_association_table).filter_by(news_articles_id=article_id, user_id=user_id).first() is not None
        return count, voted

    def toggle_upvote(self, db: Session, article_id: int, user_id: int) -> str:
        existing_upvote = db.execute(
            select(user_news_association_table).where(
                user_news_association_table.c.news_articles_id == article_id,
                user_news_association_table.c.user_id == user_id,
            )
        ).scalar()

        if existing_upvote:
            delete_stmt = delete(user_news_association_table).where(
                user_news_association_table.c.news_articles_id == article_id,
                user_news_association_table.c.user_id == user_id,
            )
            db.execute(delete_stmt)
            db.commit()
            return "Upvote removed"
        else:
            insert_stmt = insert(user_news_association_table).values(
                news_articles_id=article_id, user_id=user_id
            )
            db.execute(insert_stmt)
            db.commit()
            return "Article upvoted"

    def search_news(self, prompt: str) -> list:
        """使用 OpenAI 提取關鍵字後搜尋新聞"""
        try:
            keywords = self.ai_service.extract_keywords(prompt)
            search_term = keywords if isinstance(keywords, str) else " ".join(keywords)
            
            headlines = self.crawler.get_headline(search_term, page=1)
            news_list = []
            
            for headline in headlines:
                try:
                    news = self.crawler.parse(headline.url)
                    news_dict = news.dict()
                    news_dict["id"] = hash(str(news.url))
                    news_list.append(news_dict)
                except Exception as e:
                    print(f"Error parsing news: {e}")
            
            return sorted(news_list, key=lambda x: x["time"], reverse=True)
        except Exception as e:
            print(f"Error in search_news: {e}")
            return []

    def news_summary(self, content: str) -> dict:
        """生成新聞摘要"""
        return self.ai_service.generate_summary(content)

    def process_and_store_news(self, is_initial: bool = False) -> None:
        """抓取、處理並儲存新聞"""
        db = SessionLocal()
        try:
            pages = (1, 10) if is_initial else 1
            headlines = self.crawler.get_headline("價格", page=pages)
            
            for headline in headlines:
                relevance = self.ai_service.evaluate_relevance(headline.title)
                
                if relevance == "high":
                    try:
                        news = self.crawler.parse(headline.url)
                        summary_result = self.ai_service.generate_summary(news.content)
                        news.summary = summary_result.get("summary", "")
                        news.reason = summary_result.get("reason", "")
                        
                        self.add_news_article(db, news)
                        print(f"Saved article: {news.title}")
                    except Exception as e:
                        print(f"Error processing article: {e}")
        except Exception as e:
            print(f"Error in process_and_store_news: {e}")
        finally:
            db.close()

