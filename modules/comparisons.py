import asyncio
import difflib
import os
from itertools import product
from typing import Dict, List
from bson import ObjectId
from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient
import spacy


load_dotenv()

client = AsyncIOMotorClient(os.getenv('MONGODB_URI'))

database = client[os.getenv('DATABASE_NAME')]
visual_collection = database[os.getenv('VISUAL_COLLECTION_NAME')]
conversation_collection = database[os.getenv('CONVERSATION_COLLECTION_NAME')]

nlp = spacy.load("en_core_web_md")  # or "en_core_web_lg"

def item_fingerprint(item: Dict) -> str:
    return f"{item['name'].lower()}|{item['color'].lower()}"
    # return item['name'].strip().lower()

def jaccard_similarity(set1: set, set2: set) -> float:
    intersection = len(set1 & set2)
    union = len(set1 | set2)
    return intersection / union if union != 0 else 0

def text_similarity(text1: str, text2: str) -> float:
    return difflib.SequenceMatcher(None, text1, text2).ratio()

def nlp_similarity(a: str, b: str) -> float:
    return nlp(a).similarity(nlp(b))

def compare_object_names(doc1, doc2, threshold=0.85):
    names1 = [item["name"] for item in doc1["visual_context"]["items"]]
    names2 = [item["name"] for item in doc2["visual_context"]["items"]]

    if not names1 or not names2:
        return 0.0

    matches = []
    for name1, name2 in product(names1, names2):
        score = nlp_similarity(name1, name2)
        if score >= threshold:
            matches.append((name1, name2, score))

    return len(matches) / (len(names1) + len(names2)) * 2


async def compare_visuals(id1: str, id2: str, item_threshold=0.8, desc_threshold=0.75) -> bool:
    print("Getting documents")
    doc1 = await visual_collection.find_one({"_id": ObjectId(id1)})
    doc2 = await visual_collection.find_one({"_id": ObjectId(id2)})
    if not doc1 or not doc2:
        print("No documents")
        return False

    spacy_sim = compare_object_names(doc1, doc2)
    print(f"Item Name Vector Similarity: {round(spacy_sim, 2)*100}")

    items1 = {item_fingerprint(i) for i in doc1["visual_context"]["items"]}
    items2 = {item_fingerprint(i) for i in doc2["visual_context"]["items"]}
    item_sim = jaccard_similarity(items1, items2)
    print(f"Item Jaccard Similarity: {round(item_sim, 2)*100}%")

    desc1 = doc1["visual_context"]["description"]
    desc2 = doc2["visual_context"]["description"]
    desc_sim = text_similarity(desc1, desc2)
    print(f"Description Text Similarity: {round(desc_sim, 2)*100}%")

    loc1 = doc1["visual_context"]["image_location"]
    loc2 = doc2["visual_context"]["image_location"]
    loc_sim = text_similarity(loc1, loc2)
    print(f"Location Text Similarity: {round(loc_sim, 2)*100}%")



    return False

if __name__ == '__main__':
    asyncio.run(compare_visuals('67f1afeb060c2ce1282a220a', '67f1aff7060c2ce1282a220c'))