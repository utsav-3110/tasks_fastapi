import cloudinary
import os
from fastapi import UploadFile , File
from dotenv import load_dotenv
import  cloudinary.uploader

load_dotenv()

cloudinary.config(
    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
    api_key=os.getenv("CLOUDINARY_API_KEY"),
    api_secret=os.getenv("CLOUDINARY_API_SECRET")
)


async def create_upload_file(file: UploadFile = File(...)):
    try:
        upload_result = cloudinary.uploader.upload(file.file)
        return  upload_result.get("url")
    except Exception as e:
        return {"error": str(e)}