import logging

import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI, Request, Response, status
from fastapi.concurrency import asynccontextmanager
from pydantic import BaseModel
from svix.webhooks import Webhook, WebhookVerificationError
import ask_posthog
import os

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
async def handle_query(request: UserQueryRequest):
    logger.info(f"Received query: {request.user_query}")
    response = await ask_posthog.ask(request.user_query)
    return {
        "status": "success",
        "response": response,
        "embed_url": "https://us.posthog.com/project/97299/insights/JdSPy76X",
    }


@app.post("/dashboard_summary")
async def handle_dashboard_summary(request: DashboardSummaryRequest):
    logger.info(f"Received dashboard summary request: {request.user_query}")
    response = await ask_posthog.summarize_dashboard(request.user_query)
    return {
        "status": "success",
        "response": response,
        "embed_url": "https://us.posthog.com/project/97299/insights/JdSPy76X",
    }


@app.post("/recall/webhook", status_code=status.HTTP_204_NO_CONTENT)
async def webhook_handler(request: Request, response: Response):
    headers = request.headers
    payload = await request.body()

    try:
        wh = Webhook(os.getenv("RECALL_WEBHOOK_KEY"))
        msg = wh.verify(payload, headers)
        print(msg)
    except WebhookVerificationError as e:
        response.status_code = status.HTTP_400_BAD_REQUEST
        return

    # Do someting with the message...


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
