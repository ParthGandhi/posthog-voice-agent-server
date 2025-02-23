from enum import Enum
from typing import Optional, Dict, Any
from datetime import datetime
import os
import requests
import logging

logger = logging.getLogger(__name__)

RECALL_API_KEY = os.getenv("RECALL_API_KEY")

class RecallEventType(Enum):
    JOINING = "bot.joining"
    IN_WAITING_ROOM = "bot.in_waiting_room"
    IN_CALL_NOT_RECORDING = "bot.in_call_not_recording"
    RECORDING_PERMISSION_ALLOWED = "bot.recording_permission_allowed"
    RECORDING_PERMISSION_DENIED = "bot.recording_permission_denied"
    IN_CALL_RECORDING = "bot.in_call_recording"
    CALL_ENDED = "bot.call_ended"
    DONE = "bot.done"
    FATAL = "bot.fatal"
    RECORDING_PROCESSING = "recording.processing"


class RecallEvent:
    def __init__(self, event_data: Dict[str, Any]):
        self.raw_data = event_data
        self.event_type = event_data.get('event')
        self.bot_id = event_data.get('data', {}).get('bot', {}).get('id')
        self.bot_metadata = event_data.get('data', {}).get('bot', {}).get('metadata', {})
        
        event_data_inner = event_data.get('data', {}).get('data', {})
        self.code = event_data_inner.get('code')
        self.sub_code = event_data_inner.get('sub_code')
        self.updated_at = self._parse_datetime(event_data_inner.get('updated_at'))

    def _parse_datetime(self, dt_str: Optional[str]) -> Optional[datetime]:
        if not dt_str:
            return None
        try:
            return datetime.fromisoformat(dt_str.replace('Z', '+00:00'))
        except ValueError:
            return None

    def is_valid_event(self) -> bool:
        """Check if the event type is valid according to the RecallEventType enum"""
        try:
            RecallEventType(self.event_type)
            return True
        except ValueError:
            return False

    def get_event_description(self) -> str:
        """Return the description for the current event type"""
        event_descriptions = {
            RecallEventType.JOINING.value: 
                "The bot has acknowledged the request to join the call, and is in the process of connecting.",
            RecallEventType.IN_WAITING_ROOM.value: 
                "The bot is in the waiting room of the meeting.",
            RecallEventType.IN_CALL_NOT_RECORDING.value: 
                "The bot has joined the meeting, however is not recording yet. This could be because the bot is still setting up, does not have recording permissions, or the recording was paused.",
            RecallEventType.RECORDING_PERMISSION_ALLOWED.value: 
                "The bot has joined the meeting and it's request to record the meeting has been allowed by the host.",
            RecallEventType.RECORDING_PERMISSION_DENIED.value: 
                "The bot has joined the meeting and it's request to record the meeting has been denied.",
            RecallEventType.IN_CALL_RECORDING.value: 
                "The bot is in the meeting, and is currently recording the audio and video.",
            RecallEventType.CALL_ENDED.value: 
                "The bot has left the call, and the real-time transcription is complete.",
            RecallEventType.DONE.value: 
                "The bot has shut down. If bot produced in_call_recording event, the video is uploaded and available for download.",
            RecallEventType.FATAL.value: 
                "The bot has encountered an error that prevented it from joining the call.",
            RecallEventType.RECORDING_PROCESSING.value: 
                "The bot is processing the recording."
        }
        return event_descriptions.get(self.event_type, "Unknown event type")

async def send_audio_to_recall(bot_id: str, audio_b64: str) -> bool:
    """
    Sends base64 encoded audio to the Recall API.

    Args:
        bot_id (str): The ID of the bot to send audio to
        audio_b64 (str): Base64 encoded audio data

    Returns:
        bool: True if successful, False otherwise
    """
    url = f"https://us-west-2.recall.ai/api/v1/bot/{bot_id}/output_audio/"

    payload = {
        "kind": "mp3",
        "b64_data": audio_b64
    }
    
    headers = {
        "accept": "application/json",
        "content-type": "application/json",
        "authorization": f"Token {RECALL_API_KEY}"
    }

    try:
        response = requests.post(url, json=payload, headers=headers)
        if response.status_code != 200:
            logger.error(f"API returned error: {response.status_code} - {response.text}")
        response.raise_for_status()
        logger.info("Successfully sent audio to Recall API")
        return True
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to send audio to Recall API: {str(e)}")
        return False

async def send_screenshare_to_recall(bot_id: str, image_b64: str) -> bool:
    """
    Sends a screenshare request to the Recall API.

    Args:
        bot_id (str): The ID of the bot to send screenshare to
        image_b64 (str): Base64 encoded image data

    Returns:
        bool: True if successful, False otherwise
    """
    url = f"https://us-west-2.recall.ai/api/v1/bot/{bot_id}/output_screenshare/"

    payload = {
        "kind": "jpeg",
        "b64_data": image_b64
    }
    
    headers = {
        "accept": "application/json",
        "content-type": "application/json",
        "authorization": f"Token {RECALL_API_KEY}"
    }

    try:
        response = requests.post(url, json=payload, headers=headers)
        if response.status_code != 200:
            logger.error(f"API returned error: {response.status_code} - {response.text}")
        response.raise_for_status()
        logger.info("Successfully sent screenshare request to Recall API")
        return True
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to send screenshare request to Recall API: {str(e)}")
        return False

async def send_screenshare_stop_to_recall(bot_id: str) -> bool:
    """
    Sends a request to stop screensharing to the Recall API.

    Args:
        bot_id (str): The ID of the bot to stop screenshare for

    Returns:
        bool: True if successful, False otherwise
    """
    url = f"https://us-west-2.recall.ai/api/v1/bot/{bot_id}/output_screenshare/stop/"
    
    headers = {
        "accept": "application/json",
        "content-type": "application/json",
        "authorization": f"Token {RECALL_API_KEY}"
    }

    try:
        response = requests.post(url, headers=headers)
        if response.status_code != 200:
            logger.error(f"API returned error: {response.status_code} - {response.text}")
        response.raise_for_status()
        logger.info("Successfully sent stop screenshare request to Recall API")
        return True
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to send stop screenshare request to Recall API: {str(e)}")
        return False
