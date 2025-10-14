import os
import json
import logging
import hashlib

logger = logging.getLogger(__name__)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
RESOURCE_JSON_PATH = os.path.join(BASE_DIR, "resources.json")

def has_changed(new_data):
    """
    Description: Check if new resource data differs from existing data using MD5 hash comparison
    
    args:
        new_data: New resource data to compare against existing saved data
    
    returns:
        bool: True if data has changed or file doesn't exist, False if data is identical
    """
    if not os.path.exists(RESOURCE_JSON_PATH):
        return True
    with open(RESOURCE_JSON_PATH, "r", encoding="utf-8") as f:
        existing = json.load(f)
    old_hash = hashlib.md5(json.dumps(existing, sort_keys=True).encode()).hexdigest()
    new_hash = hashlib.md5(json.dumps(new_data, sort_keys=True).encode()).hexdigest()
    return old_hash != new_hash

# def handle_full_resource_list(message: dict):
#     file_path = os.path.join(BASE_DIR, "resources.json")
#     with open(file_path, "w", encoding="utf-8") as f:
#         json.dump(message, f, indent=4)
#     logger.info("[✓] Saved full resource list to resources.json")

def handle_full_resource_list(message: dict):
    """
    Description: Handle full resource list message by validating and saving to JSON file if data has changed
    
    args:
        message (dict): Resource data containing folders and files information
    
    returns:
        None: Saves to file if data changed, logs status messages
    """
    if not isinstance(message, dict):
        logger.warning("Received invalid data: not a dict")
        return

    if "folders" not in message or "files" not in message:
        logger.warning("Received incomplete resource data")
        return

    if has_changed(message):
        with open(RESOURCE_JSON_PATH, "w", encoding="utf-8") as f:
            json.dump(message, f, indent=4)
        logger.info("[✓] resources.json updated — content changed")
    else:
        logger.info("[~] Skipped writing resources.json — no change detected")
        
        
def handle_create_resource(message: dict):
    """
    Description: Handle create resource message by logging the received data
    
    args:
        message (dict): Create resource event data to log
    
    returns:
        None: Logs the create resource message with formatted JSON
    """
    logger.info("[→] Received 'create_resource' message:\n" + json.dumps(message, indent=4))


def handle_delete_resource(message: dict):
    """
    Description: Handle delete resource message by logging the received data
    
    args:
        message (dict): Delete resource event data to log
    
    returns:
        None: Logs the delete resource message with formatted JSON
    """
    logger.info("[→] Received 'delete_resource' message:\n" + json.dumps(message, indent=4))