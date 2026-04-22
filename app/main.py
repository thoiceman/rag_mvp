from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import uvicorn

from app.core.config import get_settings
from app.core.database import init_db
from app.models.factory import check_api_ket_set
from app.utils.logger import get_logger
from app.api.v1.router import api_router

settings = get_settings()
logger = get_logger("API")

@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        init_db()
        logger.info(f"{settings.APP_NAME} 启动：数据库初始化成功")
        
        check_api_ket_set()
        logger.info(f"{settings.APP_NAME} 启动：API Key 校验通过")
    except EnvironmentError as e:
        logger.error(f"{settings.APP_NAME} 启动失败：{str(e)}")
    yield

app = FastAPI(
    title=settings.APP_NAME,
    version="1.0.0",
    lifespan=lifespan,
    openapi_url=f"{settings.API_V1_STR}/openapi.json"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix=settings.API_V1_STR)

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
