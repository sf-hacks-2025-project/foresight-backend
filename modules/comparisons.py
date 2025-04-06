import asyncio
from difflib import SequenceMatcher
import os
from bson import ObjectId
from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient
import spacy
from concurrent.futures import ThreadPoolExecutor


load_dotenv()

client = AsyncIOMotorClient(os.getenv('MONGODB_URI'))

database = client[os.getenv('DATABASE_NAME')]
visual_collection = database[os.getenv('VISUAL_COLLECTION_NAME')]
conversation_collection = database[os.getenv('CONVERSATION_COLLECTION_NAME')]

nlp = spacy.load("en_core_web_md", disable=["ner", "parser", "tagger"])

executor = ThreadPoolExecutor()

NAME_WEIGHT = 0.4
LOCATION_WEIGHT = 0.2
COLOR_WEIGHT = 0.2
DESCRIPTION_WEIGHT = 0.2

# Preprocesses items in a document by creating 'doc' fields for the 'name', 'location', and 'description'
# These fields store the processed spaCy document objects for faster similarity comparison.
async def prepare_doc_items(items):
    for item in items:
        for key in ["name", "location", "description"]:
            item[f"{key}_doc"] = nlp(item[key])
    return items

# Quickly computes a similarity score for the 'color' field using string matching
# This function is used as a fallback for color comparison where semantic meaning isn't important.
def fast_similarity(a, b):
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()

# Compares the four key attributes ('name', 'location', 'color', 'description') between two objects
# Each attribute has a weighted contribution to the final similarity score.
def compare_objects(obj1, obj2):
    name_sim = obj1["name_doc"].similarity(obj2["name_doc"])
    loc_sim = obj1["location_doc"].similarity(obj2["location_doc"])
    color_sim = fast_similarity(obj1["color"], obj2["color"])
    desc_sim = obj1["description_doc"].similarity(obj2["description_doc"])


    return (
        name_sim * NAME_WEIGHT +
        loc_sim * LOCATION_WEIGHT +
        color_sim * COLOR_WEIGHT +
        desc_sim * DESCRIPTION_WEIGHT
    )

# Synchronously compares an object from items1 to all objects in items2 and returns the best similarity score
def compare_objects_sync(obj1, items2, threshold):
    # For each object in items2, compute the similarity score with obj1 and return the highest score
    return max(compare_objects(obj1, obj2) for obj2 in items2)

# Asynchronously compares two documents (doc1 and doc2) by processing their items and calculating similarity scores
# This function uses ThreadPoolExecutor to perform the object comparisons in parallel threads.
async def compare_docs(doc1, doc2, threshold=0.75):
    items1 = await prepare_doc_items(doc1["visual_context"]["items"])
    items2 = await prepare_doc_items(doc2["visual_context"]["items"])

    loop = asyncio.get_running_loop()

    # Schedule all comparisons in parallel threads
    tasks = [
        loop.run_in_executor(executor, compare_objects_sync, obj1, items2, threshold)
        for obj1 in items1
    ]

    scores = await asyncio.gather(*tasks)
    matched = sum(score >= threshold for score in scores)

    return matched / max(len(items1), len(items2))


# ARGS: ObjectID STR and similarity threshold
# Asynchronously compares two documents from a database based on their 'visual_context' items
# Returns True if the similarity score exceeds the specified threshold.
async def compare_visuals(id1: str, id2: str, item_threshold=0.7) -> bool:
    print("Getting documents")
    doc1 = await visual_collection.find_one({"_id": ObjectId(id1)})
    doc2 = await visual_collection.find_one({"_id": ObjectId(id2)})
    if not doc1 or not doc2:
        print("No documents")
        return False


    similarity_value = await compare_docs(doc1, doc2)
    return similarity_value > item_threshold
