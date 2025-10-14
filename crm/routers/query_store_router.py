"""
Description: Router module for storing user queries in MongoDB for analytics and monitoring purposes

args:
    None (module-level router definition)

returns:
    APIRouter: Router with query storage endpoints
"""

from fastapi import APIRouter

from crm.models.process_request import Query
from crm.utils.mongodb_connection import my_collection

router = APIRouter()

@router.post('/query')
async  def query_store(question:Query):
    """
    Description: Store user query in MongoDB collection for analytics and monitoring
    
    args:
        question (Query): Query model containing the user's question text
    
    returns:
        str: Success message confirming data storage completion
    """
    response = my_collection.insert_one({"question" : question.query})
    return "data successfully stored"