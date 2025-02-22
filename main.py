import logging

import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI
from pydantic import BaseModel

import ask_posthog

load_dotenv()

app = FastAPI()

logger = logging.getLogger(__name__)


class UserQueryRequest(BaseModel):
    user_query: str


@app.get("/")
async def root():
    return {"message": "Hello World"}


@app.post("/query")
async def handle_query(request: UserQueryRequest):
    logger.info(f"Received query: {request.user_query}")
    response = await ask_posthog.ask(request.user_query)
    return {"status": "success", "response": response}


if __name__ == "__main__":
    logger.info("Starting FastAPI application")
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        log_config="log_conf.yaml",
        reload=True,
    )
