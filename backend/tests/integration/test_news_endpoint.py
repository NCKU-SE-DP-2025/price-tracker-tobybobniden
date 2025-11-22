import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, StaticPool
from sqlalchemy.orm import sessionmaker
import json
from jose import jwt
from src.main import app
from src.db.base import Base
from src.db.models import User
from src.db.session import get_db
from src.api.v1.news.router import NewsArticle
from src.api.v1.news.service import user_news_association_table
from src.api.v1.news.schemas import NewsSummaryRequestSchema, PromptRequest
from src.api.v1.news.service import NewsService
from src.core.security import pwd_context

from unittest.mock import Mock
import os

os.environ["TESTING"] = "1"  # 告訴應用使用測試資料庫

SECRET_KEY = "1892dhianiandowqd0n"
ALGORITHM = "HS256"
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}, poolclass=StaticPool)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base.metadata.create_all(bind=engine)


def override_session_opener():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_session_opener
client = TestClient(app)

@pytest.fixture(scope="module")
def clear_users():
    with next(override_session_opener()) as db:
        db.query(User).delete()
        db.commit()

@pytest.fixture(scope="module")
def test_user(clear_users):
    hashed_password = pwd_context.hash("testpassword")

    with next(override_session_opener()) as db:
        user = User(username="testuser", hashed_password=hashed_password)
        db.add(user)
        db.commit()
        db.refresh(user)
        return user


@pytest.fixture(scope="module")
def test_token(test_user):
    access_token = jwt.encode({"sub": test_user.username}, SECRET_KEY, algorithm=ALGORITHM)
    return access_token


@pytest.fixture(scope="module")
def test_articles():
    with next(override_session_opener()) as db:
        article_1 = NewsArticle(
            url="https://example.com/test-news-1",
            title="Test News 1",
            content="This is test content 1",
            time="2024-01-01",
            summary="Test summary 1",
            reason="Test reason 1"
        )
        article_2 = NewsArticle(
            url="https://example.com/test-news-2",
            title="Test News 2",
            content="This is test content 2",
            time="2024-01-02",
            summary="Test summary 2",
            reason="Test reason 2"
        )
        db.add_all([article_1, article_2])
        db.commit()
        db.refresh(article_1)
        db.refresh(article_2)

        return [article_1, article_2]


@pytest.fixture(scope="module")
def test_user_and_articles(test_user, test_articles):
    return test_user, test_articles


def test_read_news(test_articles):
    response = client.get("/api/v1/news/")
    assert response.status_code == 200
    json_response = response.json()
    assert len(json_response) == 2
    assert json_response[0]["title"] == "Test News 2"
    assert json_response[1]["title"] == "Test News 1"


def test_read_user_news(test_user, test_token, test_articles):
    headers = {"Authorization": f"Bearer {test_token}"}
    response = client.get("/api/v1/news/user_news", headers=headers)
    print(test_token)
    print(response.json())
    assert response.status_code == 200
    json_response = response.json()
    assert len(json_response) == 2
    assert json_response[0]["title"] == "Test News 2"
    assert json_response[0]["is_upvoted"] is False
    assert json_response[1]["title"] == "Test News 1"
    assert json_response[1]["is_upvoted"] is False

def test_search_news(mocker):
    # Mock AIService methods
    mocker.patch('src.api.v1.ai.service.AIService.extract_keywords', return_value="keywords")
    
    # Mock requests.get for HTML parsing
    mock_get = mocker.patch("src.api.v1.news.service.requests.get", return_value=mocker.Mock(
        text="""
        <html>
        <h1 class="article-content__title">Test Title</h1>
        <time class="article-content__time">2024-09-10</time>
        <section class="article-content__editor">
            <p>This is a test paragraph.</p>
        </section>
        </html>
        """
    ))
    
    # Mock _fetch_raw_news_data
    mocker.patch('src.api.v1.news.service.NewsService._fetch_raw_news_data', 
                 return_value=[{"titleLink": "https://example.com/news", "title": "Test"}])

    request_body = {"prompt": "Test search prompt"}
    response = client.post("/api/v1/news/search_news", json=request_body)

    assert response.status_code == 200

def test_news_summary(mocker, test_token):
    headers = {"Authorization": f"Bearer {test_token}"}
    mocker.patch.object(NewsService, 'news_summary',
                       return_value={"summary": "test impact", "reason": "test reason"})

    request_body = NewsSummaryRequestSchema(content="Test news content")
    response = client.post("/api/v1/news/news_summary", json=request_body.dict(), headers=headers)

    assert response.status_code == 200
    json_response = response.json()
    assert json_response["summary"] == "test impact"
    assert json_response["reason"] == "test reason"


def test_upvote_article(test_user_and_articles, test_token):
    user, articles = test_user_and_articles
    headers = {"Authorization": f"Bearer {test_token}"}

    response = client.post(f"/api/v1/news/{articles[0].id}/upvote", headers=headers)
    assert response.status_code == 200
    assert response.json()["message"] == "Article upvoted"


def test_downvote_article(test_user_and_articles, test_token):
    user, articles = test_user_and_articles
    headers = {"Authorization": f"Bearer {test_token}"}

    response = client.post(f"/api/v1/news/{articles[0].id}/upvote", headers=headers)
    assert response.status_code == 200
    assert response.json()["message"] == "Upvote removed"
