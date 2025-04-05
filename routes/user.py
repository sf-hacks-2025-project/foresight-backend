from fastapi import APIRouter, HTTPException, Depends, status
from pydantic import BaseModel
import uuid
from modules import database

router = APIRouter()

# Generates a user id using uuidv4 and returns it
@router.get("/user/create", status_code=status.HTTP_200_OK)
async def register():
    return {"user_id": str(uuid.uuid4())}