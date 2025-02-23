import logging

import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.concurrency import asynccontextmanager
from pydantic import BaseModel

import ask_posthog
from ask_posthog import PosthogQueryResult

load_dotenv()


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


app = FastAPI(lifespan=lifespan)

logger = logging.getLogger(__name__)


class UserQueryRequest(BaseModel):
    user_query: str


class DashboardSummaryRequest(BaseModel):
    user_query: str


@app.get("/")
async def root():
    return {"message": "Hello World"}


@app.post("/query")
async def handle_query(request: UserQueryRequest) -> dict:
    logger.info(f"Received query: {request.user_query}")
    response: PosthogQueryResult = await ask_posthog.ask(request.user_query)
    return {
        "status": "success",
        "response": response.summary,
        "embed_url": response.embed_url,
    }


@app.post("/dashboard_summary")
async def handle_dashboard_summary(request: DashboardSummaryRequest) -> dict:
    logger.info(f"Received dashboard summary request: {request.user_query}")
    response: PosthogQueryResult = await ask_posthog.summarize_dashboard(
        request.user_query
    )
    return {
        "status": "success",
        "response": response.summary,
        "embed_url": response.embed_url,
    }


if __name__ == "__main__":
    logger.info("Starting FastAPI application")
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        log_config="log_conf.yaml",
        reload=True,
        reload_delay=2,
    )
