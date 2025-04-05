from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel
from typing import List, Optional

router = APIRouter()

class Item(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    price: float
    owner_id: int

class ItemCreate(BaseModel):
    name: str
    description: Optional[str] = None
    price: float

@router.get("/items", response_model=List[Item])
async def get_items(skip: int = 0, limit: int = 10):
    """Get all items with pagination"""
    # Implement your database query here
    # For now, return dummy data
    return [
        {"id": 1, "name": "Item 1", "description": "Description 1", "price": 10.5, "owner_id": 1},
        {"id": 2, "name": "Item 2", "description": "Description 2", "price": 20.0, "owner_id": 1}
    ]

@router.get("/items/{item_id}", response_model=Item)
async def get_item(item_id: int):
    """Get item by ID"""
    # Implement your database query here
    return {"id": item_id, "name": f"Item {item_id}", "description": f"Description {item_id}", "price": 10.0 * item_id, "owner_id": 1}

@router.post("/items", response_model=Item, status_code=201)
async def create_item(item: ItemCreate):
    """Create a new item"""
    # Implement your database insert logic here
    return {"id": 3, "name": item.name, "description": item.description, "price": item.price, "owner_id": 1}

@router.put("/items/{item_id}", response_model=Item)
async def update_item(item_id: int, item: ItemCreate):
    """Update an existing item"""
    # Implement your database update logic here
    return {"id": item_id, "name": item.name, "description": item.description, "price": item.price, "owner_id": 1}

@router.delete("/items/{item_id}", status_code=204)
async def delete_item(item_id: int):
    """Delete an item"""
    # Implement your database delete logic here
    return None 