import logging
import base64
import io
import ask_posthog
import os
import uuid
from typing import Optional
from PIL import Image, ImageDraw, ImageFont
import textwrap

from dotenv import load_dotenv
from elevenlabs import VoiceSettings
from elevenlabs.client import ElevenLabs
from recall_api import send_audio_to_recall, send_screenshare_to_recall, send_screenshare_stop_to_recall

logger = logging.getLogger(__name__)

RECALL_API_KEY = os.getenv("RECALL_API_KEY")

# Add at the top of the file, after imports
audio_cache = {}

async def process_agent_request(bot_id: str):
    """Handle agent requests by sending cached audio responses"""
    logger.info(f"Processing agent request for bot {bot_id}")
    
    try:
        # Get cached audio
        audio_b64 = audio_cache.get(bot_id)
        if not audio_b64:
            logger.error("No cached audio found for bot")
            return
            
        # Send the cached audio
        success = await send_audio_to_recall(bot_id, audio_b64)
        if not success:
            logger.error("Failed to send audio to Recall API")
            return
            
        # Clear the cache after successful send
        del audio_cache[bot_id]
        logger.info("Successfully sent cached audio response")
        
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


def create_text_image(text: str, width=1920, height=1080) -> bytes:
    """
    Creates a JPEG image with the given text.
    
    Args:
        text (str): The text to render
        width (int): Image width
        height (int): Image height
        
    Returns:
        bytes: The JPEG image data
    """
    # Create image with white background
    image = Image.new('RGB', (width, height), 'white')
    draw = ImageDraw.Draw(image)
    
    try:
        # Try to use a nice font if available
        font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 60)
    except:
        # Fallback to default font
        font = ImageFont.load_default()
    
    # Wrap text to fit width
    margin = 100
    max_width = width - 2 * margin
    wrapped_text = textwrap.fill(text, width=50)  # Adjust width as needed
    
    # Calculate text size and position
    text_bbox = draw.multiline_textbbox((0, 0), wrapped_text, font=font)
    text_width = text_bbox[2] - text_bbox[0]
    text_height = text_bbox[3] - text_bbox[1]
    
    x = (width - text_width) / 2
    y = (height - text_height) / 2
    
    # Draw text
    draw.multiline_text((x, y), wrapped_text, font=font, fill='black', align='center')
    
    # Convert to JPEG bytes
    img_byte_array = io.BytesIO()
    image.save(img_byte_array, format='JPEG')
    return img_byte_array.getvalue()


async def process_recording_started(bot_id: str) -> Optional[str]:
    """Handle the recording started event by generating audio response without sending it"""
    logger.info(f"Processing recording started for bot {bot_id}")
    
    try:
        # Get insights from PostHog
        insights = await ask_posthog.summarize_dashboard("What are my top insights from yesterday?")
        response_text = f"Here are your top insights from yesterday: {insights}"
        
        # Create and send image for screen sharing
        image_bytes = create_text_image(response_text)
        image_b64 = base64.b64encode(image_bytes).decode('utf-8')
        
        # Start screen sharing with the image
        screen_success = await send_screenshare_to_recall(bot_id, image_b64)  # Pass the image data
        if not screen_success:
            logger.error("Failed to start screen sharing")
            return None
            
        # Convert insights to speech
        audio_b64 = text_to_speech_base64(response_text)
        logger.info("Successfully generated audio response")
        
        # Store in cache
        audio_cache[bot_id] = audio_b64
        return audio_b64
        
    except Exception as e:
        logger.error(f"Error in process_recording_started: {str(e)}")
        return None


if __name__ == "__main__":
    # Test the base64 conversion
    result = text_to_speech_base64("Hello, world! This is a test of the ElevenLabs API.")
    print(f"Base64 string length: {len(result)}")