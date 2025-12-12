import sentry_sdk
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from apscheduler.schedulers.background import BackgroundScheduler

from src.core.config import settings
from src.api.v1.auth.router import router as auth_router
from src.api.v1.news.router import router as news_router
from src.api.v1.prices.router import router as prices_router
from src.api.v1.ai.service import AIService
from src.api.v1.news.service import NewsService
from src.services.scheduler_service import SchedulerService

if settings.SENTRY_DSN:
    sentry_sdk.init(
        dsn=settings.SENTRY_DSN,
        traces_sample_rate=1.0,
        profiles_sample_rate=1.0,
    )

app = FastAPI(title=settings.PROJECT_NAME, version=settings.API_VERSION)
bgs = BackgroundScheduler()

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
async def health_check():
    return {"status": "ok"}


from src.api.v1.auth.router import router as auth_router
from src.api.v1.news.router import router as news_router
from src.api.v1.prices.router import router as prices_router

app.include_router(auth_router, prefix="/api/v1")
app.include_router(news_router, prefix="/api/v1")
app.include_router(prices_router, prefix="/api/v1")

ai_service = AIService(settings.OPENAI_API_KEY)
news_service = NewsService(ai_service)
scheduler_service = SchedulerService(bgs, news_service)


@app.on_event("startup")
def start_scheduler():
    scheduler_service.start_scheduler()


@app.on_event("shutdown")
def shutdown_scheduler():
    scheduler_service.shutdown_scheduler()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)