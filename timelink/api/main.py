"""
FastAPI app for timelink

Following the tutorial at https://fastapi.tiangolo.com/tutorial/

Currently at: https://fastapi.tiangolo.com/tutorial/body/
Next: try to link to real database. See notebooks for examples.

"""
from typing import List
from enum import Enum
from fastapi import FastAPI
from pydantic import BaseModel
from datetime import date


class SearchRequest(BaseModel):
    """Search request

    Fields:
        q: search query
        after: date after which to search, possibly None
        until: date until which to search, possibly None
        skip: number of items to skip, default 0
        limit: number of items to return, default 100

    """
    q: str
    after: date | None = None  # see https://docs.pydantic.dev/usage/types/#datetime-types
    until: date | None = None
    skip: int | None = 0
    limit: int | None = 100


class SearchResults(BaseModel):
    """Search results

    Fields:
        results: list of search results
    """
    id: str
    the_class: str
    description: str
    start_date: date
    end_date: date


app = FastAPI()


@app.get("/")
async def root():
    """Timelink API end point. Check URL/docs for API documentation."""
    return {"message": "Welcome to Timelink API"}


@app.post("/search/", response_model=List[SearchResults])
async def search(search_request: SearchRequest):
    """Search for items in the database.

    Args:
        search_request: SearchRequest object

    Returns:
        Search results
    """
    result1 = SearchResults(id="jrc", 
                            the_class="person", 
                            description="Joaquim Carvalho: "+repr(search_request),
                            start_date=date(1958, 5, 24), end_date=date(2023, 1, 4))
    result2 = SearchResults(id="mag",  
                            the_class="person", 
                            description="Magda Carvalho: "+repr(search_request),
                            start_date=date(1960, 1, 1), end_date=date(2023, 1, 4)) 
    return [result1, result2]


# Tutorial
class ModelName(str, Enum):
    alexnet = "alexnet"
    resnet = "resnet"
    lenet = "lenet"


fake_items_db = [{"item_name": "Foo"}, {"item_name": "Bar"}, {"item_name": "Baz"}]


@app.get("/models/{model_name}")
async def get_model(model_name: ModelName):
    """Example of path parameters with enum validation"""
    if model_name == ModelName.alexnet:
        return {"model_name": model_name, "message": "Deep Learning FTW!"}

    if model_name.value == "lenet":
        return {"model_name": model_name, "message": "LeCNN all the images"}

    return {"model_name": model_name, "message": "Have some residuals"}


@app.get("/files/{file_path:path}")
async def read_file(file_path: str):
    """Example of path parameters"""
    return {"file_path": file_path}


@app.get("/items/")
async def read_item(skip: int = 0, limit: int = 10):
    """Example of query parameters"""
    return fake_items_db[skip: skip + limit]


@app.get("/items/{item_id}")
async def read_item(item_id: int):
    """Example of path parameters with type conversion"""
    return {"item_id": item_id}


@app.get("/items2/{item_id}")
async def read_item2(item_id: str, q: str | None = None):
    """Example of query parameters with optional
    http://127.0.0.1:8000/items2/foo?q=somequery
    http://127.0.0.1:8000/items2/foo
    """
    if q:
        return {"item_id": item_id, "q": q}
    return {"item_id": item_id}
