import json
import requests
from bs4 import BeautifulSoup
from urllib.parse import quote
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy import delete, insert, select
from src.db.models import NewsArticle, user_news_association_table
from src.db.session import engine
from src.api.v1.ai.service import AIService 

SessionLocal = sessionmaker(bind=engine)


class NewsService:
    """將新聞抓取、處理、儲存與搜尋等邏輯包裝"""

    def __init__(self, ai_service: AIService, db: Session = None): 
        self.ai_service = ai_service
        self.db = db or SessionLocal()

    def add_news_article(self, news_data: dict) -> NewsArticle:
        session = SessionLocal()
        article = NewsArticle(
            url=news_data["url"],
            title=news_data["title"],
            time=news_data["time"],
            content=" ".join(news_data["content"]) if isinstance(news_data["content"], list) else news_data["content"],
            summary=news_data.get("summary", ""),
            reason=news_data.get("reason", ""),
        )
        session.add(article)
        session.commit()
        session.refresh(article)
        session.close()
        return article

    def get_article_upvote_details(self, article_id: int, user_id: int = None):
        count = self.db.query(user_news_association_table).filter_by(news_articles_id=article_id).count()
        voted = False
        if user_id:
            voted = self.db.query(user_news_association_table).filter_by(news_articles_id=article_id, user_id=user_id).first() is not None
        return count, voted

    def toggle_upvote(self, article_id: int, user_id: int) -> str:
        existing_upvote = self.db.execute(
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
            self.db.execute(delete_stmt)
            self.db.commit()
            return "Upvote removed"
        else:
            insert_stmt = insert(user_news_association_table).values(
                news_articles_id=article_id, user_id=user_id
            )
            self.db.execute(insert_stmt)
            self.db.commit()
            return "Article upvoted"

    def search_news(self, prompt: str) -> list:
        """使用 OpenAI 提取關鍵字後搜尋新聞"""
        try:
            keywords = self.ai_service.extract_keywords(prompt)
            news_items = self._fetch_raw_news_data(keywords, is_initial=False)
            news_list = []
            
            for news in news_items:
                try:
                    response = requests.get(news["titleLink"], timeout=10)
                    soup = BeautifulSoup(response.text, "html.parser")
                    title = soup.find("h1", class_="article-content__title").text
                    time = soup.find("time", class_="article-content__time").text
                    content_section = soup.find("section", class_="article-content__editor")

                    paragraphs = [
                        paragraph_element.text
                        for paragraph_element in content_section.find_all("p")
                        if paragraph_element.text.strip() != "" and "▪" not in paragraph_element.text
                    ]
                    
                    detailed_news = {
                        "url": news["titleLink"],
                        "title": title,
                        "time": time,
                        "content": " ".join(paragraphs),
                        "id": id(news),
                    }
                    news_list.append(detailed_news)
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
        try:
            session = SessionLocal()
            news_data = self._fetch_raw_news_data("價格", is_initial=is_initial)
            
            for news in news_data:
                title = news.get("title", "")
                
                relevance = self.ai_service.evaluate_relevance(title)
                
                if relevance == "high":
                    try:
                        response = requests.get(news["titleLink"], timeout=10)
                        soup = BeautifulSoup(response.text, "html.parser")
                        
                        title = soup.find("h1", class_="article-content__title").text
                        time = soup.find("time", class_="article-content__time").text
                        content_section = soup.find("section", class_="article-content__editor")

                        paragraphs = [
                            paragraph_element.text
                            for paragraph_element in content_section.find_all("p")
                            if paragraph_element.text.strip() != "" and "▪" not in paragraph_element.text
                        ]
                        
                        detailed_news = {
                            "url": news["titleLink"],
                            "title": title,
                            "time": time,
                            "content": paragraphs,
                        }
                        
                        summary_result = self.ai_service.generate_summary(" ".join(detailed_news["content"]))  # ✅ 改：使用 AIService
                        detailed_news["summary"] = summary_result.get("summary", "")
                        detailed_news["reason"] = summary_result.get("reason", "")
                        
                        self.add_news_article(detailed_news)
                        print(f"Saved article: {title}")
                    except Exception as e:
                        print(f"Error processing article: {e}")
            session.close()
        except Exception as e:
            print(f"Error in process_and_store_news: {e}")

    def _fetch_raw_news_data(self, search_term: str, is_initial: bool = False) -> list:
        try:
            all_news_data = []
            if is_initial:
                page_results = []
                for page_num in range(1, 10):
                    query_params = {
                        "page": page_num,
                        "id": f"search:{quote(search_term)}",
                        "channelId": 2,
                        "type": "searchword",
                    }
                    response = requests.get("https://udn.com/api/more", params=query_params)
                    page_results.append(response.json()["lists"])

                for news_list in page_results:
                    all_news_data.extend(news_list)
            else:
                query_params = {
                    "page": 1,
                    "id": f"search:{quote(search_term)}",
                    "channelId": 2,
                    "type": "searchword",
                }
                response = requests.get("https://udn.com/api/more", params=query_params)
                all_news_data = response.json().get("lists", [])
            
            return all_news_data
        except Exception as e:
            print(f"Error fetching news data: {e}")
            return []