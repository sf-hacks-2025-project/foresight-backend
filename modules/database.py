import asyncio
import datetime
import os

from bson import ObjectId
from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient

from modules import comparisons
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
        "timestamp": datetime.datetime.now().timestamp()  # unix timestamp
    }
    # if len(document["visual_context"]["items"]) < 2:
    result = await visual_collection.insert_one(document)
    await _purge_on_insert(document)
    print(result)
    # else:
    #     print("Insert Failed: No Items in Document")


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

# TK Maybe we pass doc and have this be in comparisons.py
# Asynchronously compares two documents from a database based on their 'visual_context' items
# Returns True if the similarity score exceeds the specified threshold.
async def compare_visuals(id1: str, id2: str, item_threshold=0.7) -> bool:
    """
    Compares two visual documents from the database by their IDs and returns whether
    their similarity exceeds a specified threshold.

    Args:
        id1 (str): The ObjectId of the first document to compare.
        id2 (str): The ObjectId of the second document to compare.
        item_threshold (float): The similarity threshold (default is 0.7) to determine
                                 if the documents are considered a match.

    Returns:
        bool: True if the similarity score between the documents exceeds the threshold,
              False otherwise.
    """
    # print("begin")
    doc1 = await visual_collection.find_one({"_id": ObjectId(id1)})
    doc2 = await visual_collection.find_one({"_id": ObjectId(id2)})
    if not doc1 or not doc2:
        return False


    similarity_value = await comparisons.compare_docs(doc1, doc2)
    # print(similarity_value)
    return similarity_value > item_threshold


async def _find_similar_entries(doc) -> list[str]:
    """
    Find documents that are similar to the given document based on basic fields.
    This is a lightweight comparison using a low threshold for speed.
    """
    # Get all documents for the same user
    user_id = doc["user_id"]
    similar_docs = await visual_collection.find({"user_id": user_id}).to_list(length=1000)

    # Filter for documents with basic similarity checks on the fields
    filtered_docs = []
    for existing_doc in similar_docs:
        # Check if the name and color are similar enough (you can add other fields here)
        if existing_doc["_id"] != doc["_id"]:
            desc_sim = comparisons.fast_similarity(doc["visual_context"]["description"],
                                               existing_doc["visual_context"]["description"])
            # color_sim = comparisons.fast_similarity(doc["color"], existing_doc["color"])
            # If both fields have a nonzero similarity, consider the documents potentially similar enough
            if desc_sim > 0.1:
                filtered_docs.append(existing_doc["_id"])


    return filtered_docs


async def purge_duplicates_visuals(object_id: str):
    # Get all documents for a specific user
    doc = await visual_collection.find_one({"_id": ObjectId(object_id)})
    if not doc:
        return
    similar_docs_ids = await _find_similar_entries(doc)
    # print(f"Found {len(similar_docs_ids)} similar documents")
    for similar_doc_id in similar_docs_ids:
        if await compare_visuals(object_id, similar_doc_id, 0.7):
            await visual_collection.delete_one({"_id": ObjectId(similar_doc_id)})

async def _purge_on_insert(doc):
    user_id = doc["user_id"]
    recent_docs = await visual_collection.find({"user_id": user_id}).sort("timestamp", -1).limit(5).to_list(length=5)
    recent_docs = [d for d in recent_docs if str(d["_id"]) != str(doc["_id"])]

    for existing_doc in recent_docs:
        if await compare_visuals(existing_doc["_id"], doc["_id"], 0.7):
            # If the similarity is too high, delete the existing document
            await visual_collection.delete_one({"_id": existing_doc["_id"]})
            return True
    return False

