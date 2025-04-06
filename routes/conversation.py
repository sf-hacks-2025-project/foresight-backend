from fastapi import APIRouter, HTTPException, Depends, status, File, UploadFile, Form
from pydantic import BaseModel
from modules import database, gemini
import io
import asyncio
from io import BytesIO

router = APIRouter()

class TextPromptRequest(BaseModel):
    user_id: str
    text_query: str

@router.post("/conversation/text", status_code=status.HTTP_200_OK)
async def text_prompt(request: TextPromptRequest):
    try:
        print(request)
        return await gemini.generate_response(user_id=request.user_id, text_query=request.text_query)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing text prompt: {str(e)}"
        )

async def handle_transcript_task(file: BytesIO, user_id: str):
    try:
        transcription_task = await gemini.generate_audio_transcription(audio_file=file)
        await database.save_message(user_id, "user", transcription_task)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing audio: {str(e)}"
        )

@router.post("/conversation/audio", status_code=status.HTTP_200_OK)
async def audio_prompt(user_id: str = Form(...), audio_file: UploadFile = File(...)):
    try:
        contents = await audio_file.read()
        
        # Create two separate BytesIO objects with the same content
        response_audio = io.BytesIO(contents)
        transcription_audio = io.BytesIO(contents)
        
        # Run both tasks concurrently
        response_task = await gemini.generate_response(user_id, audio_file=response_audio)
        asyncio.create_task(handle_transcript_task(transcription_audio, user_id))
        await database.save_message(user_id, "assistant", response_task)
        
        return response_task
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing audio prompt: {str(e)}"
        )
    
@router.get("/conversation/clear", status_code=status.HTTP_200_OK)
async def clear_conversation(user_id: str = Form(...)):
    try:
        await database.wipe_conversation_history(user_id)
        return {"message": "Conversation history cleared successfully"}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error clearing conversation history: {str(e)}"
        )