import json
import sentry_sdk
from apscheduler.schedulers.background import BackgroundScheduler
from fastapi.middleware.cors import CORSMiddleware
import itertools
from sqlalchemy import delete, insert, select
from sqlalchemy.orm import Session, sessionmaker
from typing import List, Optional
import requests
from fastapi import APIRouter, HTTPException, Query, Depends, status, FastAPI
from datetime import datetime, timedelta
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from passlib.context import CryptContext

from pydantic import BaseModel, Field, AnyHttpUrl
from sqlalchemy import (Column, ForeignKey, Integer, String, Table, Text,
                        create_engine)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
import os
from openai import OpenAI
from urllib.parse import quote
from bs4 import BeautifulSoup

# ----------------------------
# 原來的 DB 與 Model 宣告（保留在檔案開頭）
# ----------------------------
Base = declarative_base()

user_news_association_table = Table(
    "user_news_upvotes",
    Base.metadata,
    Column("user_id", Integer, ForeignKey("users.id"), primary_key=True),
    Column(
        "news_articles_id", Integer, ForeignKey("news_articles.id"), primary_key=True
    ),
)


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(50), unique=True, nullable=False)
    hashed_password = Column(String(200), nullable=False)
    upvoted_news = relationship(
        "NewsArticle",
        secondary=user_news_association_table,
        back_populates="upvoted_by_users",
    )


class NewsArticle(Base):
    __tablename__ = "news_articles"
    id = Column(Integer, primary_key=True, autoincrement=True)
    url = Column(String, unique=True, nullable=False)
    title = Column(String, nullable=False)
    time = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    summary = Column(Text, nullable=False)
    reason = Column(Text, nullable=False)
    upvoted_by_users = relationship(
        "User", secondary=user_news_association_table, back_populates="upvoted_news"
    )


# ----------------------------
# 全域設定與 engine（保留）
# ----------------------------
engine = create_engine("sqlite:///news_database.db", echo=True)

Base.metadata.create_all(engine)

Session = sessionmaker(bind=engine)

sentry_sdk.init(
    dsn="https://4001ffe917ccb261aa0e0c34026dc343@o4505702629834752.ingest.us.sentry.io/4507694792704000",
    traces_sample_rate=1.0,
    profiles_sample_rate=1.0,
)

app = FastAPI()
bgs = BackgroundScheduler()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8080"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ----------------------------
# 工具 / 共享元件（保留變數名稱）
# ----------------------------
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/users/login")

_id_counter = itertools.count(start=1000000)


# ----------------------------
# Classes for modularization
# ----------------------------
class DatabaseManager:
    """
    負責 DB engine, session 工廠與相關操作
    """

    def __init__(self, engine):
        self.engine = engine
        self.SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)

    def session_opener(self):
        session = Session(bind=self.engine)
        try:
            yield session
        finally:
            session.close()

    # 提供一個取得 Session 的 helper（舊程式碼共用）
    def get_session(self):
        return Session(bind=self.engine)


class UserAuthService:
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
        self.pwd_context = pwd_context
        self.oauth2_scheme = oauth2_scheme
        self._jwt_secret = "1892dhianiandowqd0n"

    def verify_password(self, plain_password, hashed_password):
        return self.pwd_context.verify(plain_password, hashed_password)

    def authenticate_user(self, db: Session, username, password):
        user = db.query(User).filter(User.username == username).first()
        if not user:
            return False
        if not self.verify_password(password, user.hashed_password):
            return False
        return user

    def authenticate_user_token(
        self,
        token: str = Depends(oauth2_scheme),
        db: Session = Depends(DatabaseManager(engine).session_opener)
    ):
        payload = jwt.decode(token, self._jwt_secret, algorithms=["HS256"])
        return db.query(User).filter(User.username == payload.get("sub")).first()

    def create_access_token(self, data, expires_delta=None):
        to_encode = data.copy()
        expire = datetime.utcnow() + (expires_delta or timedelta(minutes=15))
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, self._jwt_secret, algorithm="HS256")
        return encoded_jwt


class NewsService:
    """
    將新聞抓取、處理、儲存與搜尋等邏輯封裝
    """

    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
        # 使用外部 OpenAI 客戶端時，保留現有寫法（api_key 放 "xxx" 作為 placeholder）
        self.openai_api_key = "xxx"

    def add_news_article(self, news_data):
        """
        Add news article to database
        :param news_data: news info dictionary
        :return: None
        """
        session = Session()
        session.add(
            NewsArticle(
                url=news_data["url"],
                title=news_data["title"],
                time=news_data["time"],
                content=" ".join(news_data["content"]),  # 將內容list轉換為字串
                summary=news_data.get("summary", ""),
                reason=news_data.get("reason", ""),
            )
        )
        session.commit()
        session.close()

    def fetch_raw_news_data(self, search_term, is_initial=False):
        """
        從新聞來源獲取原始新聞資料
        :param search_term: 搜尋關鍵字
        :param is_initial: 是否為初始化抓取
        :return: 新聞資料列表
        """
        all_news_data = []
        # iterate pages to get more news data, not actually get all news data
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
                all_news_data.append(news_list)
        else:
            page_num = {
                "page": 1,
                "id": f"search:{quote(search_term)}",
                "channelId": 2,
                "type": "searchword",
            }
            response = requests.get("https://udn.com/api/more", params=page_num)

            all_news_data = response.json()["lists"]
        return all_news_data

    def process_and_store_news(self, is_initial=False):
        """
        Fetch and process news articles
        :param is_initial: whether to fetch initial data
        :return: None
        """
        news_data = self.fetch_raw_news_data("價格", is_initial=is_initial)
        for news in news_data:
            title = news["title"]
            prompt_message = [
                {
                    "role": "system",
                    "content": "你是一個關聯度評估機器人，請評估新聞標題是否與「民生用品的價格變化」相關，並給予'high'、'medium'、'low'評價。(僅需回答'high'、'medium'、'low'三個詞之一)",
                },
                {"role": "user", "content": f"{title}"},
            ]
            ai = OpenAI(api_key=self.openai_api_key).chat.completions.create(
                model="gpt-3.5-turbo",
                messages=prompt_message,
            )
            relevance = ai.choices[0].message.content
            if relevance == "high":
                response = requests.get(news["titleLink"])
                soup = BeautifulSoup(response.text, "html.parser")
                # 標題
                title = soup.find("h1", class_="article-content__title").text
                time = soup.find("time", class_="article-content__time").text
                # 定位到包含文章内容的 <section>
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

                completion = OpenAI(api_key=self.openai_api_key).chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=prompt_message,
                )
                result = completion.choices[0].message.content
                result = json.loads(result)
                detailed_news["summary"] = result["影響"]
                detailed_news["reason"] = result["原因"]
                self.add_news_article(detailed_news)

    def get_article_upvote_details(self, article_id, user_id, db):
        count = (
            db.query(user_news_association_table)
            .filter_by(news_articles_id=article_id)
            .count()
        )
        voted = False
        if user_id:
            voted = (
                db.query(user_news_association_table)
                .filter_by(news_articles_id=article_id, user_id=user_id)
                .first()
                is not None
            )
        return count, voted

    def search_news(self, prompt: str):
        """
        使用 OpenAI 提取關鍵字後搜尋（原 search_news 的邏輯）
        """
        message = [
            {
                "role": "system",
                "content": "你是一個關鍵字提取機器人，用戶將會輸入一段文字，表示其希望看見的新聞內容，請提取出用戶希望看見的關鍵字，請截取最重要的關鍵字即可，避免出現「新聞」、「資訊」等混淆搜尋引擎的字詞。(僅須回答關鍵字，若有多個關鍵字，請以空格分隔)",
            },
            {"role": "user", "content": f"{prompt}"},
        ]

        completion = OpenAI(api_key=self.openai_api_key).chat.completions.create(
            model="gpt-3.5-turbo",
            messages=message,
        )
        keywords = completion.choices[0].message.content
        news_items = self.fetch_raw_news_data(keywords, is_initial=False)
        news_list = []
        for news in news_items:
            try:
                response = requests.get(news["titleLink"])
                soup = BeautifulSoup(response.text, "html.parser")
                # 標題
                title = soup.find("h1", class_="article-content__title").text
                time = soup.find("time", class_="article-content__time").text
                # 定位到包含文章内容的 <section>
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
                detailed_news["content"] = " ".join(detailed_news["content"])
                detailed_news["id"] = next(_id_counter)
                news_list.append(detailed_news)
            except Exception as e:
                print(e)
        return sorted(news_list, key=lambda x: x["time"], reverse=True)

    def news_summary(self, content: str):
        message = [
            {
                "role": "system",
                "content": "你是一個新聞摘要生成機器人，請統整新聞中提及的影響及主要原因 (影響、原因各50個字，請以json格式回答 {'影響': '...', '原因': '...'})",
            },
            {"role": "user", "content": f"{content}"},
        ]

        completion = OpenAI(api_key=self.openai_api_key).chat.completions.create(
            model="gpt-3.5-turbo",
            messages=message,
        )
        result = completion.choices[0].message.content
        if result:
            result = json.loads(result)
            return {"summary": result["影響"], "reason": result["原因"]}
        return {}

    def toggle_upvote(self, article_id, user_id, db):
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

    def news_exists(self, news_id_2, db: Session):
        return db.query(NewsArticle).filter_by(id=news_id_2).first() is not None


class SchedulerService:
    """
    封裝與排程、FastAPI 啟動/停止相關的邏輯
    """

    def __init__(self, bgs: BackgroundScheduler, db_manager: DatabaseManager, news_service: NewsService):
        self.bgs = bgs
        self.db_manager = db_manager
        self.news_service = news_service

    def start_scheduler(self):
        db = SessionLocal()
        if db.query(NewsArticle).count() == 0:
            # should change into simple factory pattern
            self.news_service.process_and_store_news()
        db.close()
        self.bgs.add_job(self.news_service.process_and_store_news, "interval", minutes=100)
        self.bgs.start()

    def shutdown_scheduler(self):
        self.bgs.shutdown()


class AppFactory:
    """
    保留來做應用層級整合（目前主要為示範用途）
    """

    def __init__(self, app: FastAPI, db_manager: DatabaseManager, auth_service: UserAuthService, news_service: NewsService, scheduler_service: SchedulerService):
        self.app = app
        self.db_manager = db_manager
        self.auth_service = auth_service
        self.news_service = news_service
        self.scheduler_service = scheduler_service

    # 可擴充：註冊路由、middleware 等（目前檔案已以頂層函數保留）
    def register(self):
        pass


# ----------------------------
# 建立 class 實例
# ----------------------------
db_manager = DatabaseManager(engine)
auth_service = UserAuthService(db_manager)
news_service = NewsService(db_manager)
scheduler_service = SchedulerService(bgs, db_manager, news_service)
app_factory = AppFactory(app, db_manager, auth_service, news_service, scheduler_service)

# ----------------------------
# 以下保留所有原先的函數名稱（順序與名稱皆保留），但內部轉發到 class 方法
# ----------------------------

def add_news_article(news_data):
    """
    Add news article to database
    :param news_data: news info dictionary
    :return: None
    """
    return news_service.add_news_article(news_data)


def fetch_raw_news_data(search_term, is_initial=False):
    """
    從新聞來源獲取原始新聞資料
    :param search_term: 搜尋關鍵字
    :param is_initial: 是否為初始化抓取
    :return: 新聞資料列表
    """
    return news_service.fetch_raw_news_data(search_term, is_initial=is_initial)


def process_and_store_news(is_initial=False):
    """
    Fetch and process news articles
    :param is_initial: whether to fetch initial data
    :return: None
    """
    return news_service.process_and_store_news(is_initial=is_initial)


@app.on_event("startup")
def start_scheduler():
    return scheduler_service.start_scheduler()


@app.on_event("shutdown")
def shutdown_scheduler():
    return scheduler_service.shutdown_scheduler()


def session_opener():
    # 保持原名稱與 generator 行為
    session = Session(bind=engine)
    try:
        yield session
    finally:
        session.close()


def verify_password(plain_password, hashed_password):
    return auth_service.verify_password(plain_password, hashed_password)


def authenticate_user(db, username, password):
    # 保持名稱與相同行為（與原本 authenticate_user 一樣）
    return auth_service.authenticate_user(db, username, password)


def authenticate_user_token(
    token = Depends(oauth2_scheme),
    db = Depends(session_opener)
):
    # 仍保留原本函數簽章（Depends 內容不變）
    payload = jwt.decode(token, '1892dhianiandowqd0n', algorithms=["HS256"])
    return db.query(User).filter(User.username == payload.get("sub")).first()


def create_access_token(data, expires_delta=None):
    """create access token"""
    return auth_service.create_access_token(data, expires_delta=expires_delta)


@app.post("/api/v1/users/login")
async def login_for_access_token(
        form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(session_opener)
):
    """login"""
    user = authenticate_user(db, form_data.username, form_data.password)
    access_token = create_access_token(
        data={"sub": str(user.username)}, expires_delta=timedelta(minutes=30)
    )
    return {"access_token": access_token, "token_type": "bearer"}


class UserAuthSchema(BaseModel):
    username: str
    password: str

@app.post("/api/v1/users/register")
def create_user(user: UserAuthSchema, db: Session = Depends(session_opener)):
    """create user"""
    hashed_password = pwd_context.hash(user.password)
    db_user = User(username=user.username, hashed_password=hashed_password)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


@app.get("/api/v1/users/me")
def read_current_user(user=Depends(authenticate_user_token)):
    """
    讀取目前登入的使用者資訊
    """
    return {"username": user.username}


def get_article_upvote_details(article_id, user_id, db):
    return news_service.get_article_upvote_details(article_id, user_id, db)


@app.get("/api/v1/news/news")
def get_news_articles(db=Depends(session_opener)):
    """
    Get all news articles
    :param db: database session
    :return: list of news articles with upvote info
    """
    news_articles = db.query(NewsArticle).order_by(NewsArticle.time.desc()).all()
    result = []
    for article in news_articles:
        upvotes_count, is_upvoted = get_article_upvote_details(article.id, None, db)
        result.append(
            {**article.__dict__, "upvotes": upvotes_count, "is_upvoted": is_upvoted}
        )
    return result


@app.get(
    "/api/v1/news/user_news"
)
def read_user_news(
        db=Depends(session_opener),
        user=Depends(authenticate_user_token)
):
    """
    read user new

    :param db:
    :param u:
    :return:
    """
    news = db.query(NewsArticle).order_by(NewsArticle.time.desc()).all()
    result = []
    for article in news:
        upvotes, upvoted = get_article_upvote_details(article.id, user.id, db)
        result.append(
            {
                **article.__dict__,
                "upvotes": upvotes,
                "is_upvoted": upvoted,
            }
        )
    return result


class PromptRequest(BaseModel):
    prompt: str

@app.post("/api/v1/news/search_news")
async def search_news(request: PromptRequest):
    prompt = request.prompt
    return news_service.search_news(prompt)


class NewsSummaryRequestSchema(BaseModel):
    content: str

@app.post("/api/v1/news/news_summary")
async def news_summary(
        payload: NewsSummaryRequestSchema, u=Depends(authenticate_user_token)
):
    response = news_service.news_summary(payload.content)
    return response


@app.post("/api/v1/news/{id}/upvote")
def upvote_article(
        news_id,
        db=Depends(session_opener),
        user=Depends(authenticate_user_token),
):
    message = news_service.toggle_upvote(news_id, user.id, db)
    return {"message": message}


def toggle_upvote(article_id, user_id, db):
    return news_service.toggle_upvote(article_id, user_id, db)


def news_exists(news_id_2, db: Session):
    return news_service.news_exists(news_id_2, db)


@app.get("/api/v1/prices/necessities-price")
def get_necessities_prices(
        category=Query(None), commodity=Query(None)
):
    return requests.get(
        "https://opendata.ey.gov.tw/api/ConsumerProtection/NecessitiesPrice",
        params={"CategoryName": category, "Name": commodity},
    ).json()
