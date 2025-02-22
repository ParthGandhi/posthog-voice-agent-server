import uvicorn
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()


class UserQueryRequest(BaseModel):
    user_query: str


@app.post("/query")
async def handle_query(request: UserQueryRequest):
    return {"status": "success", "received_query": request.user_query}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
