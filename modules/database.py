import datetime
import os
from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient
from utils.common import calculate_relative_timestamp
import asyncio
import nest_asyncio

load_dotenv()

client = AsyncIOMotorClient(os.getenv('MONGODB_URI'))

database = client[os.getenv('DATABASE_NAME')]
visual_collection = database[os.getenv('VISUAL_COLLECTION_NAME')]
conversation_collection = database[os.getenv('CONVERSATION_COLLECTION_NAME')]

def run_sync(coro):
    try:
        return asyncio.run(coro)
    except RuntimeError as e:
        nest_asyncio.apply()
        loop = asyncio.get_event_loop()
        return loop.run_until_complete(coro)

def fetch_history(user_id: str) -> list[dict]:
    """Fetches the history of what we saw in around the user along with the relative timestamp of when it occurred.
    Args:
        user_id: The ID of the user.

    Returns:
        A list of dictionaries containing what items we saw in around the user along with the relative timestamp of when it occurred.
    """
    return run_sync(_fetch_history_async(user_id))

async def _fetch_history_async(user_id: str) -> list[dict]:
    cursor = visual_collection.find({"user_id": user_id})
    
    history = []
    async for document in cursor:
        history.append({
            "visual_context": document["visual_context"],
            "relative_timestamp": calculate_relative_timestamp(document["timestamp"])
        })
    
    return history

def get_conversation_history(user_id: str):
    """Retrieves the conversation history for a user.
    Args:
        user_id: The ID of the user.

    Returns:
        A list of messages in the conversation history, ordered by timestamp.
    """
    return run_sync(_get_conversation_history_async(user_id))
    
async def _get_conversation_history_async(user_id: str) -> list[dict]:
    cursor = conversation_collection.find({"user_id": user_id}).sort("timestamp", 1).limit(20)
    
    history = []
    async for document in cursor:
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
    await conversation_collection.insert_one(document)

async def save_visual_context(user_id, visual_context: dict):
    document = {
        "user_id": user_id,
        "visual_context": visual_context,
        "timestamp": datetime.datetime.now().timestamp() # unix timestamp
    }
    result = await visual_collection.insert_one(document)
    print(result)

async def wipe_conversation_history(user_id: str):
    await conversation_collection.delete_many({"user_id": user_id})

async def wipe_visual_history(user_id: str):
    await visual_collection.delete_many({"user_id": user_id})