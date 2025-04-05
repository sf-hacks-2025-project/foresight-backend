import os
from functools import lru_cache

from motor.motor_asyncio import AsyncIOMotorClient

MONGO_URL = os.environ["MONGODB_URI"]

@lru_cache()
def get_db_client():
    return AsyncIOMotorClient(MONGO_URL)

def get_db():
    db_client = get_db_client()
    return db_client["database"]

