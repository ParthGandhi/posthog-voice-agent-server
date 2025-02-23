import logging
import base64
import io
import ask_posthog
import os
import uuid

from dotenv import load_dotenv
from elevenlabs import VoiceSettings
from elevenlabs.client import ElevenLabs
from recall_api import send_audio_to_recall

logger = logging.getLogger(__name__)

RECALL_API_KEY = os.getenv("RECALL_API_KEY")

async def process_agent_request(bot_id: str):
    """Handle agent requests by generating and sending audio responses"""
    logger.info(f"Processing agent request for bot {bot_id}")
    
    try:
        # Get insights from PostHog
        insights = await ask_posthog.summarize_dashboard("What are my top insights from yesterday?")
        response_text = f"Here are your top insights from yesterday: {insights}"
        
        # Convert insights to speech
        audio_b64 = text_to_speech_base64(response_text)
        
        success = await send_audio_to_recall(bot_id, audio_b64)
        if not success:
            logger.error("Failed to send audio to Recall API")
            return
            
        logger.info("Successfully processed agent request and sent audio response")
        
    except Exception as e:
        logger.error(f"Error in process_agent_request: {str(e)}")
        
    return


ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")

if not ELEVENLABS_API_KEY:
    raise ValueError("ELEVENLABS_API_KEY environment variable not set")

client = ElevenLabs(
    api_key=ELEVENLABS_API_KEY,
)


def text_to_speech_base64(text: str) -> str:
    """
    Converts text to speech and returns the audio as a base64 encoded string.

    This function uses a specific client for text-to-speech conversion. It configures
    various parameters for the voice output and returns the audio data as a base64 string.

    Args:
        text (str): The text content to convert to speech.

    Returns:
        str: The base64 encoded audio data.
    """
    # Calling the text_to_speech conversion API with detailed parameters
    response = client.text_to_speech.convert(
        voice_id="pNInz6obpgDQGcFmaJgB",  # Adam pre-made voice
        optimize_streaming_latency="0",
        output_format="mp3_22050_32",
        text=text,
        model_id="eleven_turbo_v2",  # use the turbo model for low latency
        voice_settings=VoiceSettings(
            stability=0.0,
            similarity_boost=1.0,
            style=0.0,
            use_speaker_boost=True,
        ),
    )

    # Collect all chunks into a single bytes object
    buffer = io.BytesIO()
    for chunk in response:
        if chunk:
            buffer.write(chunk)
    
    # Convert to base64
    audio_bytes = buffer.getvalue()
    audio_b64 = base64.b64encode(audio_bytes).decode('utf-8')
    
    logger.info("Audio successfully converted to base64")
    return audio_b64


if __name__ == "__main__":
    # Test the base64 conversion
    result = text_to_speech_base64("Hello, world! This is a test of the ElevenLabs API.")
    print(f"Base64 string length: {len(result)}")