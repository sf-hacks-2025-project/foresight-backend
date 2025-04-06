import asyncio
import os
from difflib import SequenceMatcher
from dotenv import load_dotenv
import spacy
from concurrent.futures import ThreadPoolExecutor

from numpy.ma.extras import average

load_dotenv()

parent_dir = os.path.dirname((os.path.dirname(__file__)))
model_dir = os.path.join(parent_dir, "static", "en_core_web_md-3.8.0")
nlp = spacy.load(model_dir, disable=["ner", "parser", "tagger"])

executor = ThreadPoolExecutor()

NAME_WEIGHT = 0.4
LOCATION_WEIGHT = 0.2
COLOR_WEIGHT = 0.2
DESCRIPTION_WEIGHT = 0.2

# Preprocesses items in a document by creating 'doc' fields for the 'name', 'location', and 'description'
# These fields store the processed spaCy document objects for faster similarity comparison.
async def _prepare_doc_items(items):
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
def _compare_objects_sync(obj1, items2):
    # For each object in items2, compute the similarity score with obj1 and return the highest score
    return max(compare_objects(obj1, obj2) for obj2 in items2)

# Asynchronously compares two documents (doc1 and doc2) by processing their items and calculating similarity scores
# This function uses ThreadPoolExecutor to perform the object comparisons in parallel threads.
# TK forgot to check image_location & description
async def compare_docs(doc1, doc2, threshold=0.75):
    items1 = await _prepare_doc_items(doc1["visual_context"]["items"])
    items2 = await _prepare_doc_items(doc2["visual_context"]["items"])

    # figure this out later
    if len(items1) < 2 and len(items2) < 2: # if both are near empty of items
        return 1.00 # we should do description & image_location comparison only

    loop = asyncio.get_running_loop()

    # Schedule all comparisons in parallel threads
    tasks = [
        loop.run_in_executor(executor, _compare_objects_sync, obj1, items2)
        for obj1 in items1
    ]

    scores = await asyncio.gather(*tasks)
    return average(scores)
    # matched = sum(score >= threshold for score in scores)
    # return matched / max(len(items1), len(items2))





