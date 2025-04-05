from fastapi import APIRouter, HTTPException, Depends, status, File, UploadFile, Form
from pydantic import BaseModel
from modules import database, gemini
import io

router = APIRouter()

# Handles visual context saving and retrieval, API should receive an image and then call get_visual_context
class VisualContextResponse(BaseModel):
    message: str
    visual_context: dict

@router.post("/vision/upload", response_model=VisualContextResponse, status_code=status.HTTP_200_OK)
async def upload_image(user_id: str = Form(...), image: UploadFile = File(...)):
    """Upload an image and get visual context
    
    Args:
        user_id: The ID of the user
        image: The image file to process
        
    Returns:
        A dictionary containing the visual context
    """
    try:
        # Read the image file
        contents = await image.read()
        
        # Process the image using gemini
        visual_context = await gemini.get_visual_context(io.BytesIO(contents))
        
        # Save the visual context to the database
        await database.save_visual_context(user_id, visual_context)
        
        return {
            "message": "Image processed successfully",
            "visual_context": visual_context
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing image: {str(e)}"
        )

@router.get("/vision/clear", status_code=status.HTTP_200_OK)
async def clear_vision(user_id: str = Form(...)):
    try:
        await database.wipe_visual_history(user_id)
        return {"message": "Visual history cleared successfully"}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error clearing visual history: {str(e)}"
        )