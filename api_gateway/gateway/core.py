import httpx
from fastapi import HTTPException, Request, Response, status, File, UploadFile, Form
from typing import List, Optional, Dict, Any, Union, Callable
from importlib import import_module
import base64
from pydantic import BaseModel
from contextlib import asynccontextmanager
import functools
from starlette.datastructures import UploadFile as StarletteUploadFile


class APIError(Exception):
    def __init__(self, status_code: int, detail: str, headers: Optional[Dict[str, str]] = None):
        self.status_code = status_code
        self.detail = detail
        self.headers = headers or {}
        super().__init__(detail)

class RequestError(APIError):
    def __init__(self, detail: str, status_code: int = status.HTTP_400_BAD_REQUEST):
        super().__init__(status_code=status_code, detail=detail)

class AuthenticationError(APIError):
    def __init__(self, detail: str, status_code: int = status.HTTP_401_UNAUTHORIZED):
        super().__init__(
            status_code=status_code,
            detail=detail,
            headers={"WWW-Authenticate": "Bearer"}
        )

class HTTPClient:
    @staticmethod
    @asynccontextmanager
    async def get_client():
        """Context manager for HTTP client"""
        async with httpx.AsyncClient() as client:
            yield client

    @staticmethod
    async def make_request(
        url: str,
        method: str,
        data: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        timeout: float = 30.0
    ) -> tuple[Any, int]:
        """Make HTTP request with error handling"""
        headers = headers or {}
        
        try:
            async with HTTPClient.get_client() as client:
                response = await client.request(
                    method=method.upper(),
                    url=url,
                    json=data,
                    headers=headers,
                    timeout=timeout
                )
                response.raise_for_status()
                return response.json(), response.status_code
                
        except httpx.HTTPStatusError as e:
            error_detail = (
                e.response.json().get('detail', str(e))
                if e.response.headers.get('content-type') == 'application/json'
                else str(e)
            )
            raise APIError(
                status_code=e.response.status_code,
                detail=error_detail,
                headers={'WWW-Authenticate': 'Bearer'}
            )
        except httpx.RequestError:
            raise APIError(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail='Service is unavailable.',
                headers={'WWW-Authenticate': 'Bearer'}
            )
        except Exception:
            raise APIError(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail='Internal server error'
            )

class ModuleImporter:
    @staticmethod
    def import_function(method_path: str) -> Callable:
        """Import function from module path"""
        try:
            module, method = method_path.rsplit('.', 1)
            mod = import_module(module)
            return getattr(mod, method)
        except (ImportError, AttributeError) as e:
            raise RequestError(
                f"Failed to import function: {method_path}",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

def route(
    request_method: Any,
    path: str,
    status_code: int,
    payload_key: str,
    service_url: str,
    authentication_required: bool = False,
    post_processing_func: Optional[str] = None,
    authentication_token_decoder: str = 'auth.decode_access_token',
    service_authorization_checker: str = 'auth.is_admin_user',
    service_header_generator: str = 'auth.generate_request_header',
    response_model: Optional[str] = None,
    response_list: bool = False,
    files: bool = False
):
    """Enhanced route decorator with improved organization and error handling"""
    
    if response_model:
        try:
            response_model_class = ModuleImporter.import_function(response_model)
            if response_list:
                response_model_class = List[response_model_class]
        except Exception:
            raise RequestError(
                "Failed to import response model",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    else:
        response_model_class = None

    real_link = request_method(
        path,
        response_model=response_model_class,
        status_code=status_code
    )

    def wrapper(func):
        @real_link
        @functools.wraps(func)
        async def inner(request: Request, response: Response, **kwargs):
            service_headers = {}

            if authentication_required:
                await handle_authentication(
                    request,
                    authentication_token_decoder,
                    service_authorization_checker,
                    service_header_generator,
                    service_headers
                )

            try:
                method = request.method.lower()
                url = f'{service_url}{request.url.path}'
                payload = await process_payload(files, payload_key, kwargs)
           
                resp_data, status_code_from_service = await HTTPClient.make_request(
                    url=url,
                    method=method,
                    data=payload,
                    headers=service_headers,
                )
                response.status_code = status_code_from_service
                return resp_data

            except APIError:
                raise
            except Exception:
                raise APIError(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Internal server error"
                )

        return inner
    return wrapper

async def handle_authentication(
    request: Request,
    token_decoder_path: str,
    auth_checker_path: str,
    header_generator_path: str,
    service_headers: Dict[str, str]
) -> None:
    """Handle authentication and authorization"""
    authorization = request.headers.get('authorization')
    if not authorization:
        raise AuthenticationError("Authorization header missing")

    try:
        token_decoder = ModuleImporter.import_function(token_decoder_path)
        token_payload = token_decoder(authorization)

        if auth_checker_path:
            authorization_check = ModuleImporter.import_function(auth_checker_path)
            if not authorization_check(token_payload):
                raise AuthenticationError(
                    "Insufficient permissions",
                    status_code=status.HTTP_403_FORBIDDEN
                )

        if header_generator_path:
            header_generator = ModuleImporter.import_function(header_generator_path)
            service_headers.update(header_generator(token_payload))

    except APIError:
        raise
    except Exception as e:
        raise AuthenticationError(str(e))

async def process_payload(files: bool, payload_key: str, kwargs: Dict[str, Any]) -> Optional[Any]:
   
    print("okay",type(kwargs.get(payload_key)))
    payload_obj = kwargs.get(payload_key)
    if not payload_obj:
        return None

    if files:
        try:
            if isinstance(payload_obj, list):
                
                if all(isinstance(item, StarletteUploadFile) for item in payload_obj):
                    processed_files = []
                    for file in payload_obj:
                        file_content = await file.read()
                       
                        processed_files.append({
                            'filename': file.filename,
                            'content': base64.b64encode(file_content).decode('utf-8'),
                            'content_type': file.content_type
                        })
                    return {payload_key: processed_files}
                
            elif isinstance(payload_obj, dict):
                # Handle dictionary with FastAPI UploadFiles
                processed_payload = {}
                for key, value in payload_obj.items():
                    if isinstance(value, UploadFile):
                        file_content = await value.read()
                        processed_payload[key] = {
                            'filename': value.filename,
                            'content': base64.b64encode(file_content).decode('utf-8'),
                            'content_type': value.content_type
                        }
                    elif isinstance(value, list) and all(isinstance(f, UploadFile) for f in value):
                        processed_payload[key] = []
                        for file in value:
                            file_content = await file.read()
                            processed_payload[key].append({
                                'filename': file.filename,
                                'content': base64.b64encode(file_content).decode('utf-8'),
                                'content_type': file.content_type
                            })
                    else:
                        processed_payload[key] = value
                return processed_payload
                
            elif isinstance(payload_obj, BaseModel):
                # Handle Pydantic model
                return payload_obj.model_dump()
                
        except Exception as e:
            print(f"Error processing files: {str(e)}")  # Debug logging
            raise RequestError(f"Failed to process file upload: {str(e)}")
    else:
        return payload_obj.model_dump() if isinstance(payload_obj, BaseModel) else payload_obj