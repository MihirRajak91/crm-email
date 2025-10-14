import os
import pymongo
import logging
from dotenv import load_dotenv
from crm.utils.logger import logger
from crm.core.settings import get_settings

# # Load environment variables
# load_dotenv()

# # Fetching environment variables
# mongodb_host = os.getenv('MONGODB_HOST')
# mongodb_username = os.getenv('MONGODB_USERNAME')
# mongodb_password = os.getenv('MONGODB_PASSWORD')
# mongodb_db = os.getenv('MONGODB_DB', 'chatdb')
# mongodb_collection = os.getenv('MONGODB_COLLECTION', 'chats')
# print("mongo_host :", mongodb_host)
# print("mongo_username :", mongodb_username)
# print("mongo_password :", mongodb_password)
# print("mongo_db :", mongodb_db)
# print("mongo_collection :", mongodb_collection)

# # Validate that MONGODB_HOST is provided
# if not mongodb_host:
#     raise EnvironmentError("MONGODB_HOST environment variable is not set.")

# # Construct the MongoDB URI
# if mongodb_username and mongodb_password:
#     mongo_uri = f"mongodb://{mongodb_username}:{mongodb_password}@{mongodb_host}/{mongodb_db}?authSource=admin"
# else:
#     mongo_uri = f"mongodb://{mongodb_host}/{mongodb_db}"

settings = get_settings()
mongo_uri = settings.mongodb_uri
mongodb_db = settings.MONGODB_DB_NAME
mongodb_collection = settings.MONGODB_DB_NAME
logger.info(f"Connecting to MongoDB at: {mongo_uri}")

# Attempting to connect to MongoDB
try:    
    myclient = pymongo.MongoClient(mongo_uri, serverSelectionTimeoutMS=5000)
    mydb = myclient[mongodb_db]
    my_collection = mydb[mongodb_collection]
    logger.info("Successfully connected to MongoDB.")
except pymongo.errors.ServerSelectionTimeoutError as e:
    logger.error(f"MongoDB connection failed: {e}")
    raise
except Exception as e:
    logger.error(f"Unexpected error occurred while connecting to MongoDB: {e}")
    raise

def get_mongodb_client():
    """
    Description: Get the shared MongoDB client instance for database operations
    
    args:
        None
    
    returns:
        pymongo.MongoClient: MongoDB client instance for database connections
    """
    return myclient

def get_database(db_name: str = mongodb_db):
    """
    Description: Get a MongoDB database instance by name using the shared client
    
    args:
        db_name (str): Name of the database to access, defaults to configured mongodb_db
    
    returns:
        pymongo.database.Database: MongoDB database instance for collection operations
    """
    return myclient[db_name]

def get_collection(db_name: str = mongodb_db, collection_name: str = mongodb_collection):
    """
    Description: Get a MongoDB collection instance by database and collection name
    
    args:
        db_name (str): Name of the database, defaults to configured mongodb_db
        collection_name (str): Name of the collection, defaults to configured mongodb_collection
    
    returns:
        pymongo.collection.Collection: MongoDB collection instance for document operations
    """
    return myclient[db_name][collection_name]
