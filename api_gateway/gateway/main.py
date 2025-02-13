from fastapi import FastAPI, status, Request, Response,UploadFile,File
from typing import Tuple,List
import httpx
from conf.conf import settings
from core import route
from schema.auth import UpdateSchema,LoginSchema,DeleteSchema,RegisterSchema

app = FastAPI()
@route(
    request_method=app.post,
    path='/login',
    status_code=status.HTTP_201_CREATED,
    service_url=settings.AUTH_SERVICE_URL,
    payload_key="login_data",
    authentication_required=False,
    response_model=''
)
async def login(login_data:LoginSchema,request: Request, response: Response):
    pass

@route(
    request_method=app.post,
    path='/register',
    status_code=status.HTTP_201_CREATED,
    service_url=settings.AUTH_SERVICE_URL,
    payload_key="resgister_data",
    authentication_required=False,
    response_model=''
)
async def register(resgister_data:RegisterSchema,request: Request, response: Response):
    pass

@route(
    request_method=app.delete,
    path='/delete',
    status_code=status.HTTP_201_CREATED,
    service_url=settings.AUTH_SERVICE_URL,
    payload_key="delete_id",
    authentication_required=False,
    response_model=''
)
async def delete(delete_id: DeleteSchema,request: Request, response: Response):
    # erro r when the int value start with zero
    pass

@route(
    request_method=app.put,
    path='/update',
    status_code=status.HTTP_201_CREATED,
    service_url=settings.AUTH_SERVICE_URL,
    payload_key="update_data",
    authentication_required=False,
    response_model=''
)
async def update(update_data:UpdateSchema,request: Request, response: Response):
    pass

@route(
    request_method=app.post,
    path="/text_file",
    status_code=status.HTTP_201_CREATED,
    service_url=settings.MLDATASET_SERVICE_URL,
    payload_key="single_file",
    authentication_required=False,
    response_model='',
    files=True
)
async def file_upload_multiple(request:Request,response:Response,single_file: List[UploadFile] = File(...),):
    pass

@route(
    request_method=app.post,
    path="/image_files",
    status_code=status.HTTP_201_CREATED,
    service_url=settings.MLDATASET_SERVICE_URL,
    payload_key="single_file",
    authentication_required=False,
    response_model='',
    files=True
)
async def image_upload_multiple(request:Request,response:Response,single_file: List[UploadFile] = File(...),):
    pass
