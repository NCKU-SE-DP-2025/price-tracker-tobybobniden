import json
import requests
from bs4 import BeautifulSoup
from openai import OpenAI
from urllib.parse import quote
from sqlalchemy.orm import Session
from sqlalchemy import delete, insert, select
from src.core.config import settings
from src.db.models import NewsArticle, user_news_association_table


class NewsService:
    def __init__(self):
        self.openai_client = OpenAI(api_key=settings.OPENAI_API_KEY)

    def add_news_article(self, news_data: dict) -> NewsArticle:
        session = Session()
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
        try:
            message = [
                {
                    "role": "system",
                    "content": "你是一個關鍵字提取機器人，用戶將會輸入一段文字，表示其希望看見的新聞內容，請提取出用戶希望看見的關鍵字，請截取最重要的關鍵字即可，避免出現「新聞」、「資訊」等混淆搜尋引擎的字詞。(僅須回答關鍵字，若有多個關鍵字，請以空格分隔)",
                },
                {"role": "user", "content": f"{prompt}"},
            ]

            completion = self.openai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=message,
            )
            keywords = completion.choices[0].message.content
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
        try:
            message = [
                {
                    "role": "system",
                    "content": "你是一個新聞摘要生成機器人，請統整新聞中提及的影響及主要原因 (影響、原因各50個字，請以json格式回答 {'影響': '...', '原因': '...'})",
                },
                {"role": "user", "content": f"{content}"},
            ]

            completion = self.openai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=message,
            )
            result = completion.choices[0].message.content
            if result:
                result = json.loads(result)
                return {"summary": result.get("影響", ""), "reason": result.get("原因", "")}
            return {"summary": "", "reason": ""}
        except Exception as e:
            print(f"Error in news_summary: {e}")
            return {"summary": "", "reason": ""}

    def process_and_store_news(self, is_initial: bool = False) -> None:
        try:
            session = Session()
            news_data = self._fetch_raw_news_data("價格", is_initial=is_initial)
            for news in news_data:
                title = news.get("title", "")
                
                prompt_message = [
                    {
                        "role": "system",
                        "content": "你是一個關鍵度評估機器人，請評估新聞標題是否與「民生用品的價格變化」相關，並給予'high'、'medium'、'low'評價。(僅需回答'high'、'medium'、'low'三個詞之一)",
                    },
                    {"role": "user", "content": f"{title}"},
                ]
                
                ai = self.openai_client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=prompt_message,
                )
                relevance = ai.choices[0].message.content.strip()
                
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
                        
                        prompt_message = [
                            {
                                "role": "system",
                                "content": "你是一個新聞摘要生成機器人，請統整新聞中提及的影響及主要原因 (影響、原因各50個字，請以json格式回答 {'影響': '...', '原因': '...'})",
                            },
                            {"role": "user", "content": " ".join(detailed_news["content"])},
                        ]

                        completion = self.openai_client.chat.completions.create(
                            model="gpt-3.5-turbo",
                            messages=prompt_message,
                        )
                        result = completion.choices[0].message.content
                        result = json.loads(result)
                        detailed_news["summary"] = result.get("影響", "")
                        detailed_news["reason"] = result.get("原因", "")
                        
                        self.add_news_article(detailed_news)
                    except Exception as e:
                        print(f"Error processing article: {e}")
        except Exception as e:
            print(f"Error in process_and_store_news: {e}")

    def _fetch_raw_news_data(self, search_term: str, is_initial: bool = False) -> list:
        try:
            all_news_data = []
            if is_initial:
                for page_num in range(1, 10):
                    query_params = {
                        "page": page_num,
                        "id": f"search:{quote(search_term)}",
                        "channelId": 2,
                        "type": "searchword",
                    }
                    response = requests.get("https://udn.com/api/more", params=query_params, timeout=10)
                    all_news_data.extend(response.json()["lists"])
            else:
                query_params = {
                    "page": 1,
                    "id": f"search:{quote(search_term)}",
                    "channelId": 2,
                    "type": "searchword",
                }
                response = requests.get("https://udn.com/api/more", params=query_params, timeout=10)
                all_news_data = response.json().get("lists", [])
            
            return all_news_data
        except Exception as e:
            print(f"Error fetching news data: {e}")
            return []