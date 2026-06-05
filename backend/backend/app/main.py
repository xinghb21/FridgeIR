from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router
from app.core.config import get_settings
from app.db.init_db import init_db

settings = get_settings()

app = FastAPI(title=settings.app_name)

# 当后端部署到远程服务器、前端运行在另一个域名或端口时，
# 浏览器会要求后端显式允许该前端来源。默认不启用，
# 需要时通过 .env 中的 CORS_ALLOWED_ORIGINS 配置。
if settings.cors_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

app.include_router(router)


@app.on_event("startup")
def startup() -> None:
    # MVP 阶段为了方便演示，服务启动时自动建表。
    # 进入正式环境前，建议改成 Alembic 迁移管理。
    init_db()
