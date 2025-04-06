from fastapi import APIRouter, HTTPException, Depends, status, File, UploadFile, Form
from pydantic import BaseModel
from modules import database, gemini
import io
import asyncio

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

@router.post("/conversation/audio", status_code=status.HTTP_200_OK)
async def audio_prompt(user_id: str = Form(...), audio_file: UploadFile = File(...)):
    try:
        contents = await audio_file.read()
        
        # Create two separate BytesIO objects with the same content
        response_audio = io.BytesIO(contents)
        transcription_audio = io.BytesIO(contents)
        
        # Run both tasks concurrently
        response_task = gemini.generate_response(user_id, audio_file=response_audio)
        transcription_task = gemini.generate_audio_transcription(audio_file=transcription_audio)
        
        # Await both tasks
        results = await asyncio.gather(response_task, transcription_task)
        
        # Extract results
        response_text = results[0]
        transcription = results[1]

        # You can log the transcription or use it as needed
        print(f"Audio transcription: {transcription}")

        asyncio.create_task(database.save_message(user_id, "user", transcription))
        
        return response_text
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