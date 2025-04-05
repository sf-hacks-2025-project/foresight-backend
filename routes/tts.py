from io import BytesIO

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
        voice_id="9BWtsMINqrJLrRacOk9x", # We can have a dropdown to change this
        output_format="mp3_22050_32",
        text=text,
        model_id="eleven_flash_v2_5",
        voice_settings=VoiceSettings(
            stability=0.0,
            similarity_boost=1.0,
            style=0.0,
            use_speaker_boost=True,
            speed=1.0,
        ),
    )

    audio_data = BytesIO()
    async for chunk in response:
        if chunk:
            audio_data.write(chunk)

    audio_data.seek(0)  # rewind to start

    return StreamingResponse(
        audio_data,
        media_type="audio/mpeg",
        headers={"Content-Disposition": "attachment; filename=output.mp3"}
    )