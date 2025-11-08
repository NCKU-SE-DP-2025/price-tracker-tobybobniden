from apscheduler.schedulers.background import BackgroundScheduler
from sqlalchemy.orm import sessionmaker
from src.db.models import NewsArticle
from src.db.session import engine
from src.api.v1.news.service import NewsService


class SchedulerService:
    def __init__(self, bgs: BackgroundScheduler, news_service: NewsService):
        self.bgs = bgs
        self.news_service = news_service

    def start_scheduler(self):
        from src.db.models import NewsArticle
        from src.db.session import SessionLocal
        
        db = SessionLocal()
        if db.query(NewsArticle).count() == 0:
            self.news_service.process_and_store_news(is_initial=True)
        db.close()
        
        self.bgs.add_job(self.news_service.process_and_store_news, "interval", minutes=100)
        self.bgs.start()

    def shutdown_scheduler(self):
        if self.bgs.running:
            self.bgs.shutdown()