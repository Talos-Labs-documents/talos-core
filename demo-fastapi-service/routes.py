from fastapi import APIRouter
from models import Item

router = APIRouter()


fake_db = []


@router.post("/items")
def create_item(item: Item):
    fake_db.append(item)
    return {"status": "created", "item": item}


@router.get("/items")
def list_items():
    return fake_db