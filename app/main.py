import os
from fastapi import FastAPI, Body, HTTPException, status
from fastapi.responses import Response, JSONResponse
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel, Field, EmailStr
from bson import ObjectId
from typing import Optional, List
import motor.motor_asyncio

app = FastAPI()
client = motor.motor_asyncio.AsyncIOMotorClient(os.environ["MONGODB_URL"])
db = client.archive


class PyObjectId(ObjectId):
    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v):
        if not ObjectId.is_valid(v):
            raise ValueError("Invalid objectid")
        return ObjectId(v)

    @classmethod
    def __get_pydantic_json_schema__(cls, field_schema):
        field_schema.update(type="string")


class VideoModel(BaseModel):
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    videoId: str = Field(...)
    channelId: str = Field(...)
    channelName: str = Field(...)
    title: str = Field(...)
    platform: str = Field(...)

    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}
        json_schema_extra = {
            "example": {
                "videoId": "4bLd42hHc2k",
                "channelId": "@kjvbiblereadalong",
                "channelName": "KJV Bible Read Along",
                "title": "Bible Book 18. Job Complete - King James 1611 KJV Read Along - Diverse Readers Dramatized Theme",
                "platform": "youtube",
            }
        }


class UpdateVideoModel(BaseModel):
    videoId: Optional[str]
    channelId: Optional[str]
    channelName: Optional[str]
    title: Optional[str]
    platform: Optional[str]

    class Config:
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}
        json_schema_extra = {
            "example": {
                "videoId": "4bLd42hHc2k",
                "channelId": "@kjvbiblereadalong",
                "channelName": "KJV Bible Read Along",
                "title": "Bible Book 18. Job Complete - King James 1611 KJV Read Along - Diverse Readers Dramatized Theme",
                "platform": "youtube",
            }
        }


@app.post("/", response_description="Add new video", response_model=VideoModel)
async def create_video(video: VideoModel = Body(...)):
    video = jsonable_encoder(video)
    new_video = await db["videos"].insert_one(video)
    created_video = await db["videos"].find_one({"_id": new_video.inserted_id})
    return JSONResponse(status_code=status.HTTP_201_CREATED, content=created_video)


@app.get(
    "/", response_description="List all videos", response_model=List[VideoModel]
)
async def list_videos():
    videos = await db["videos"].find().to_list(1000)
    return videos


@app.get(
    "/{id}", response_description="Get a single video", response_model=VideoModel
)
async def show_video(id: str):
    if (video := await db["videos"].find_one({"_id": id})) is not None:
        return video

    raise HTTPException(status_code=404, detail=f"Video {id} not found")


@app.put("/{id}", response_description="Update a video", response_model=VideoModel)
async def update_video(id: str, video: UpdateVideoModel = Body(...)):
    video = {k: v for k, v in video.dict().items() if v is not None}

    if len(video) >= 1:
        update_result = await db["videos"].update_one({"_id": id}, {"$set": video})

        if update_result.modified_count == 1:
            if (
                updated_video := await db["videos"].find_one({"_id": id})
            ) is not None:
                return updated_video

    if (existing_video := await db["videos"].find_one({"_id": id})) is not None:
        return existing_video

    raise HTTPException(status_code=404, detail=f"Video {id} not found")


@app.delete("/{id}", response_description="Delete a video")
async def delete_video(id: str):
    delete_result = await db["videos"].delete_one({"_id": id})

    if delete_result.deleted_count == 1:
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    raise HTTPException(status_code=404, detail=f"Video {id} not found")
