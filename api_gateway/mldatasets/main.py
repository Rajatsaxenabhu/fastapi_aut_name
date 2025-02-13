from fastapi import FastAPI,status
from pathlib import Path
from schema.ml_schema import TextSchema
from fastapi.responses import JSONResponse
from typing import List
from pydantic import BaseModel
from fastapi import File,UploadFile
from typing import Any
import base64
app=FastAPI()

class FileData(BaseModel):
    filename: str
    content: str  
    content_type: str

class FileUploadRequest(BaseModel):
    single_file: List[FileData]


def re_encode(content: str) -> str:  
    encoded= base64.b64decode(content).decode('utf-8')
    return encoded

def re_encode_img(content: str) -> str:  
    encoded= base64.b64decode(content)
    return encoded

@app.post('/text_file',status_code=status.HTTP_201_CREATED)
async def file_upload_multiple(request:FileUploadRequest):
    try:
        print(len(request.single_file))
        for fl in request.single_file:
            print("filename",fl.filename)
            print("content",re_encode(fl.content))
        return JSONResponse(content={"message":"text upload successfully"},status_code=status.HTTP_201_CREATED)
    except Exception as err:
        print(str(err))
        return JSONResponse(content={"message":"text upload failed"},status_code=status.HTTP_400_BAD_REQUEST)

@app.post('/image_files',status_code=status.HTTP_201_CREATED)
async def image_upload_multiple(request:FileUploadRequest):
    print("inside the image uploads")
    save_path = Path('media')
    save_path.mkdir(exist_ok=True)
    try:
        print(len(request.single_file))
        for fl in request.single_file:
            print("filename",fl.filename)
            img_data=re_encode_img(fl.content)
            with open(f"media/{fl.filename}", "wb") as f:
                f.write(img_data)
        return JSONResponse(content={"message":"text upload successfully"},status_code=status.HTTP_201_CREATED)
    except Exception as err:
        print(str(err))
        return JSONResponse(content={"message":"image upload failed"},status_code=status.HTTP_400_BAD_REQUEST)


@app.post('/multiple_files',status_code=status.HTTP_201_CREATED)
async def multi_files_upload():
    pass
