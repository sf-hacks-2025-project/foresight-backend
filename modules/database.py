import datetime
import os
from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient
from utils.common import calculate_relative_timestamp, run_sync

load_dotenv()

client = AsyncIOMotorClient(os.getenv('MONGODB_URI'))

database = client[os.getenv('DATABASE_NAME')]
visual_collection = database[os.getenv('VISUAL_COLLECTION_NAME')]
conversation_collection = database[os.getenv('CONVERSATION_COLLECTION_NAME')]

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

def search_visual_contexts(user_id: str, keywords: list[str], limit: int = 5) -> list[dict]:
    """
    Search for visual contexts that contain any of the provided keywords.
    
    Args:
        user_id: The ID of the user.
        keywords: List of keywords to search for in visual contexts.
        limit: Maximum number of results to return.
        
    Returns:
        A list of matching visual contexts with their relative timestamps.
    """
    return run_sync(_search_visual_contexts_async(user_id, keywords, limit))

async def _search_visual_contexts_async(user_id: str, keywords: list[str], limit: int = 10) -> list[dict]:
    # Create a regex pattern for case-insensitive search of any keyword
    # This will match if any keyword appears in the JSON string representation of visual_context
    if not keywords or len(keywords) == 0:
        # If no keywords provided, return most recent contexts
        return await _fetch_history_async(user_id, limit)
    
    # Prepare the query - we'll search in the visual_context field
    # We need to search in the stringified JSON since MongoDB doesn't support
    # searching within nested JSON structures without text indexes
    query = {
        "user_id": user_id,
        "$or": []
    }
    
    # Add a condition for each keyword
    for keyword in keywords:
        if keyword and len(keyword.strip()) > 0:
            # Escape special regex characters
            escaped_keyword = keyword.replace(".", "\\.").replace("*", "\\*").replace("[", "\\[").replace("]", "\\]")
            query["$or"].append({
                "$or": [
                    # Search in description
                    {"visual_context.description": {"$regex": escaped_keyword, "$options": "i"}},
                    # Search in image_location
                    {"visual_context.image_location": {"$regex": escaped_keyword, "$options": "i"}},
                    # Search in items names
                    {"visual_context.items.name": {"$regex": escaped_keyword, "$options": "i"}},
                    # Search in items descriptions
                    {"visual_context.items.description": {"$regex": escaped_keyword, "$options": "i"}},
                    # Search in items locations
                    {"visual_context.items.location": {"$regex": escaped_keyword, "$options": "i"}},
                    # Search in items colors
                    {"visual_context.items.color": {"$regex": escaped_keyword, "$options": "i"}}
                ]
            })
    
    # If no valid keywords were added, return recent contexts
    if len(query["$or"]) == 0:
        return await _fetch_history_async(user_id, limit)
    
    # Execute the query, sort by timestamp (newest first)
    cursor = visual_collection.find(query).sort("timestamp", -1).limit(limit)
    
    # Process results
    history = []
    async for document in cursor:
        history.append({
            "visual_context": document["visual_context"],
            "relative_timestamp": calculate_relative_timestamp(document["timestamp"])
        })
    
    return history

def search_visual_contexts_sync(user_id: str, keywords: list[str], limit: int = 10) -> list[dict]:
    """
    Synchronous wrapper for search_visual_contexts.
    
    Args:
        user_id: The ID of the user.
        keywords: List of keywords to search for in visual contexts.
        limit: Maximum number of results to return.
        
    Returns:
        A list of matching visual contexts with their relative timestamps.
    """
    return run_sync(search_visual_contexts(user_id, keywords, limit))