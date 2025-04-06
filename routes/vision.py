from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from modules import database, gemini
import io
import base64
from PIL import Image, ImageStat

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
        
        # Validate image before processing
        image_bytes = io.BytesIO(image_data)
        if not is_valid_image(image_bytes):
            return {
                "message": "Image appears to be a black screen or solid color. Please ensure your camera is uncovered.",
                "visual_context": {
                    "image_location": "Unknown",
                    "description": "The image appears to be a black screen or solid color. Please ensure your camera is uncovered.",
                    "items": []
                }
            }
        
        # Reset the BytesIO position after validation
        image_bytes.seek(0)
        
        # Process the image using gemini
        visual_context = await gemini.get_visual_context(image_bytes)
        
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

def is_valid_image(image_bytes):
    """
    Check if an image is valid (not a black screen or solid color).
    
    Args:
        image_bytes: BytesIO object containing the image data
        
    Returns:
        bool: True if the image is valid, False otherwise
    """
    try:
        # Open the image
        img = Image.open(image_bytes)
        
        # Convert to RGB if not already
        if img.mode != 'RGB':
            img = img.convert('RGB')
        
        # Get image statistics
        stat = ImageStat.Stat(img)
        
        # Calculate the standard deviation of each channel
        # Low std dev means the image is mostly a solid color
        r_std, g_std, b_std = stat.stddev
        
        # Calculate brightness
        brightness = sum(stat.mean) / 3
        
        # Check if the image is too dark (black screen)
        if brightness < 20:  # Threshold for darkness
            print("Image rejected: Too dark (likely black screen)")
            return False
        
        # Check if the image has very little variation (solid color)
        if r_std < 10 and g_std < 10 and b_std < 10:  # Threshold for variation
            print("Image rejected: Low variation (likely solid color)")
            return False
            
        # Additional check for nearly identical RGB values (grayscale)
        means = stat.mean
        if abs(means[0] - means[1]) < 5 and abs(means[1] - means[2]) < 5 and abs(means[0] - means[2]) < 5:
            # If it's grayscale, ensure it has enough contrast
            if max(stat.stddev) < 20:
                print("Image rejected: Grayscale with low contrast")
                return False
        
        # Reset the file pointer
        image_bytes.seek(0)
        return True
        
    except Exception as e:
        print(f"Error validating image: {str(e)}")
        # If there's an error, let it pass through to be processed
        # This avoids blocking legitimate images that might have format issues
        image_bytes.seek(0)
        return True

@router.get("/vision/clear", status_code=status.HTTP_200_OK)
async def clear_vision(user_id: str):
    try:
        await database.wipe_visual_history(user_id)
        return {"message": "Visual history cleared successfully"}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error clearing visual history: {str(e)}"
        )