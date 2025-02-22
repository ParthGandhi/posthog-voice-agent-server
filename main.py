import logging

import uvicorn
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()

logger = logging.getLogger(__name__)


class UserQueryRequest(BaseModel):
    user_query: str


@app.post("/query")
async def handle_query(request: UserQueryRequest):
    logger.info(f"Received query: {request.user_query}")
    return {"status": "success", "received_query": request.user_query}


if __name__ == "__main__":
    logger.info("Starting FastAPI application")
    uvicorn.run(app, host="0.0.0.0", port=8000, log_config="log_conf.yaml")
