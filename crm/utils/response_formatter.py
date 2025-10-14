from fastapi.responses import JSONResponse
from typing import List, Dict, Any

def format_success_response(data: Any, message: str = "Success") -> JSONResponse:
    """
    Description: Format a successful response with data and a message for API endpoints
    
    args:
        data (Any): The data to include in the response
        message (str): A success message, defaults to "Success"
    
    returns:
        JSONResponse: A formatted JSON response with status, message, and data fields
    """
    return JSONResponse(
        status_code=200,
        content={
            "status": "success",
            "message": message,
            "data": data
        }
    )

def format_error_response(error_message: str, status_code: int = 400) -> JSONResponse:
    """
    Description: Format an error response with an error message and status code for API endpoints
    
    args:
        error_message (str): The error message to include in the response
        status_code (int): The HTTP status code for the error response, defaults to 400
    
    returns:
        JSONResponse: A formatted JSON response for the error with status and message fields
    """
    return JSONResponse(
        status_code=status_code,
        content={
            "status": "error",
            "message": error_message
        }
    )