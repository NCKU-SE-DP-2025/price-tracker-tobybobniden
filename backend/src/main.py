import sentry_sdk
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from apscheduler.schedulers.background import BackgroundScheduler

from src.core.config import settings

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


# 導入並註冊路由
from src.api.v1.auth.router import router as auth_router
from src.api.v1.news.router import router as news_router
from src.api.v1.prices.router import router as prices_router
from src.api.v1.news.service import NewsService
from src.services.scheduler_service import SchedulerService

print(f"Registering routers...")
app.include_router(auth_router, prefix="/api/v1")
print(f"✓ auth_router registered")
app.include_router(news_router, prefix="/api/v1")
print(f"✓ news_router registered")
app.include_router(prices_router, prefix="/api/v1")
print(f"✓ prices_router registered")

print(f"\nTotal routes: {len(app.routes)}")
for route in app.routes:
    if hasattr(route, 'methods'):
        print(f"  {route.methods}: {route.path}")

news_service = NewsService()
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