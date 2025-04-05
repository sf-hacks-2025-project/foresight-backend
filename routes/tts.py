from fastapi import APIRouter, status
from modules import eleven_labs
from elevenlabs import AsyncElevenLabs, VoiceSettings
from fastapi.responses import StreamingResponse
import os

router = APIRouter()

@router.get("/tts/generate", status_code=status.HTTP_200_OK)
async def tts(text: str):
    client: AsyncElevenLabs = await eleven_labs.get_eleven_client()
    response = client.text_to_speech.convert(
        voice_id=os.getenv('ELEVEN_LABS_VOICE_ID'),
        output_format="mp3_22050_32",
        text=text,
        model_id="eleven_flash_v2_5",
        voice_settings=VoiceSettings(
            stability=0.0,
            similarity_boost=1.0,
            style=0.0,
            use_speaker_boost=True,
            speed=1.05,
        ),
    )

    async def audio_streamer():
        async for chunk in response:
            if chunk:
                yield chunk

    return StreamingResponse(audio_streamer(), media_type="audio/mpeg")