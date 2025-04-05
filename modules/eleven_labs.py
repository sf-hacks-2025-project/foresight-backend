from elevenlabs.client import AsyncElevenLabs
from dotenv import load_dotenv
import os

load_dotenv()

client = AsyncElevenLabs(
    api_key=os.getenv('ELEVEN_LABS_KEY'),
)

async def get_eleven_client():
    return client