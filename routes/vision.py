from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from modules import database, gemini
import io
import base64

router = APIRouter()

# Handles visual context saving and retrieval, API should receive an image and then call get_visual_context
class ImageUploadRequest(BaseModel):
    user_id: str
    image_base64: str

class VisualContextResponse(BaseModel):
    message: str
    visual_context: dict

@router.post("/vision/upload", response_model=VisualContextResponse, status_code=status.HTTP_200_OK)
async def upload_image(request: ImageUploadRequest):
    """Upload a base64 encoded image and get visual context
    
    Args:
        request: ImageUploadRequest containing user_id and base64 encoded image
        
    Returns:
        A dictionary containing the visual context
    """
    try:
        # Decode base64 image
        try:
            image_data = base64.b64decode(request.image_base64)
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid base64 image data"
            )
        
        # Process the image using gemini
        visual_context = await gemini.get_visual_context(io.BytesIO(image_data))
        
        # Save the visual context to the database
        await database.save_visual_context(request.user_id, visual_context)
        
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