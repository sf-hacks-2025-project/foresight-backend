import datetime
import os
from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import MongoClient
from utils.common import calculate_relative_timestamp

load_dotenv()

# Async client for API endpoints
async_client = AsyncIOMotorClient(os.getenv('MONGODB_URI'))
async_db = async_client[os.getenv('DATABASE_NAME')]
async_visual_collection = async_db[os.getenv('VISUAL_COLLECTION_NAME')]
async_conversation_collection = async_db[os.getenv('CONVERSATION_COLLECTION_NAME')]

# Sync client for Gemini tool functions
sync_client = MongoClient(os.getenv('MONGODB_URI'))
sync_db = sync_client[os.getenv('DATABASE_NAME')]
sync_visual_collection = sync_db[os.getenv('VISUAL_COLLECTION_NAME')]
sync_conversation_collection = sync_db[os.getenv('CONVERSATION_COLLECTION_NAME')]


def fetch_history(user_id: str) -> list[dict]:
    """Fetches the history of what we saw in around the user along with the relative timestamp of when it occurred.
    Args:
        user_id: The ID of the user.

    Returns:
        A list of dictionaries containing what items we saw in around the user along with the relative timestamp of when it occurred.
    """
    cursor = sync_visual_collection.find({"user_id": user_id})
    history = []
    for document in cursor:
        history.append({
            "visual_context": document["visual_context"],
            "relative_timestamp": calculate_relative_timestamp(document["timestamp"])
        })
    return history

def get_conversation_history(user_id: str) -> list[dict]:
    """Retrieves the conversation history for a user.
    Args:
        user_id: The ID of the user.

    Returns:
        A list of messages in the conversation history, ordered by timestamp.
    """
    cursor = sync_conversation_collection.find({"user_id": user_id}).sort("timestamp", 1).limit(20)
    history = []
    for document in cursor:
        history.append({
            "role": document["role"],
            "content": document["content"]
        })
    return history

async def save_message(user_id: str, role: str, content: str):
    """Saves a message to the conversation history.
    Args:
        user_id: The ID of the user.
        role: The role of the message sender (user or assistant).
        content: The content of the message.
    """
    document = {
        "user_id": user_id,
        "role": role,
        "content": content,
        "timestamp": datetime.datetime.now().timestamp()
    }
    await async_conversation_collection.insert_one(document)

async def save_visual_context(user_id, visual_context: dict):
    document = {
        "user_id": user_id,
        "visual_context": visual_context,
        "timestamp": datetime.datetime.now().timestamp() # unix timestamp
    }
    result = await async_visual_collection.insert_one(document)
    print(result)

async def wipe_conversation_history(user_id: str):
    await async_conversation_collection.delete_many({"user_id": user_id})

async def wipe_visual_history(user_id: str):
    await async_visual_collection.delete_many({"user_id": user_id})