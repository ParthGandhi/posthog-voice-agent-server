import logging
import json
from datetime import datetime, timedelta
import hashlib

import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI, Request, Response, status
from fastapi.concurrency import asynccontextmanager
from pydantic import BaseModel
from svix.webhooks import Webhook, WebhookVerificationError
import ask_posthog
import os
from recall_api import RecallEvent, RecallEventType
from agent import process_agent_request, process_recording_started

load_dotenv()

# Add at the top level of the file
last_response_time = None
COOLDOWN_SECONDS = 30  # Adjust this value as needed

# Track processed transcripts using their IDs
processed_transcripts = set()

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
        # Parse the verified message into a RecallEvent
        recall_event = RecallEvent(msg)
        
        if not recall_event.is_valid_event():
            logger.warning(f"Invalid event type received: {recall_event.event_type}")
            response.status_code = status.HTTP_400_BAD_REQUEST
            return
            
        logger.info(f"Received valid Recall event: {recall_event.event_type}")
        logger.info(f"Event description: {recall_event.get_event_description()}")
        logger.info(f"Bot ID: {recall_event.bot_id}")
        logger.info(f"Event code: {recall_event.code}")
        logger.info(f"Event sub_code: {recall_event.sub_code}")
        logger.info(f"Updated at: {recall_event.updated_at}")
        
        # Check if this is the IN_CALL_RECORDING event
        if recall_event.event_type == RecallEventType.IN_CALL_RECORDING.value:
            logger.info("Bot is now recording, generating audio response")
            await process_recording_started(recall_event.bot_id)
            
    except WebhookVerificationError as e:
        logger.error(f"Webhook verification failed: {str(e)}")
        response.status_code = status.HTTP_400_BAD_REQUEST
        return


@app.post("/api/webhook/recall/transcript", status_code=status.HTTP_204_NO_CONTENT)
async def handle_transcript(request: Request, response: Response):
    logger.info("Received transcript request")
    body = await request.body()
    
    try:
        data = json.loads(body.decode())
        
        # Get transcript ID
        transcript_id = data.get('data', {}).get('transcript', {}).get('id')
        if not transcript_id:
            logger.error("No transcript ID found in request")
            response.status_code = status.HTTP_400_BAD_REQUEST
            return
            
        # Check if we've already processed this transcript
        if transcript_id in processed_transcripts:
            logger.info(f"Already processed transcript {transcript_id}")
            return

        words = data.get('data', {}).get('data', {}).get('words', [])
        bot_id = data.get('data', {}).get('bot', {}).get('id')
        
        if not bot_id:
            logger.error("No bot ID found in request")
            response.status_code = status.HTTP_400_BAD_REQUEST
            return
        
        # Extract and concatenate all text from words
        transcript_text = ' '.join(word.get('text', '') for word in words)
        logger.info(f"Transcript text: {transcript_text}")
        
        # Make the trigger phrase more specific
        if "daily stand up" in transcript_text.strip().lower():
            logger.info("Found trigger phrase in transcript")
            processed_transcripts.add(transcript_id)  # Mark this transcript as processed
            await process_agent_request(bot_id)
            
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse JSON: {str(e)}")
        response.status_code = status.HTTP_400_BAD_REQUEST
    except Exception as e:
        logger.error(f"Error processing transcript: {str(e)}")
        response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    
    return

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
