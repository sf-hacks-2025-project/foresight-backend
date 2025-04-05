import asyncio
import os
from email import message
from functools import lru_cache

from motor.motor_asyncio import AsyncIOMotorClient

MONGO_URL = os.environ["MONGODB_URI"]


@lru_cache()
def get_db_client():
    return AsyncIOMotorClient(MONGO_URL)


def get_db():
    db_client = get_db_client()
    return db_client["database"]


# from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
from enum import Enum


class RoleEnum(str, Enum):
    user: str = 'user'
    agent: str = 'agent'


class Message(BaseModel):
    session_id: str
    role: RoleEnum
    message: str
    timestamp: datetime

class InputStatus(BaseModel):
    status: str
    memory_id: str
    timestamp: datetime


# Gets the
async def get_messages(session_id: str) -> List[Message]:
    """Get item by ID"""
    cursor = get_db()["messages"].find({"session_id": session_id})
    result = await cursor.to_list(length=100)

    msg_list = []
    for msg in result:
        msg_list.append(Message(
            session_id=session_id,
            role=RoleEnum(msg["role"]),
            message=msg["message"],
            timestamp=msg["timestamp"]
        ))

    # Implement your database query here
    return msg_list


async def add_message(msg: Message):
    """Add a new message"""
    try:
        if msg.timestamp is None:
            msg.timestamp = datetime.utcnow()

        memory_data = {
            "session_id": msg.session_id,
            "role": msg.role,
            "message": msg.message,
            "timestamp": msg.timestamp}

        result = await get_db()["messages"].insert_one(memory_data)

        return InputStatus(
            status="success",
            memory_id=str(result.inserted_id),
            timestamp=msg.timestamp.isoformat()
        )

    except Exception as e:
        print(e)
        return None


async def delete_item(item_id: int):
    """Delete an item"""
    # Implement your database delete logic here
    return None


async def test_coroutine():
    my_message = Message(
        session_id="andrey-loves-men",
        role=RoleEnum.user,
        message="Where did I leave my keys?",
        timestamp=datetime.utcnow()
    )
    await add_message(my_message)
    print(await get_messages("andrey-loves-men"))


if __name__ == "__main__":
    asyncio.run(test_coroutine())
