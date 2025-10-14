from typing import List, Optional
from datetime import datetime
import uuid
from pymongo import MongoClient
from crm.models.process_request import ConversationMessage, Conversation
from crm.utils.mongodb_connection import get_mongodb_client, get_database, get_collection
from bson import ObjectId
from crm.utils.logger import logger

class ConversationManager:
    """
    Description: Manages conversation history and context for follow-up questions using MongoDB with embedded messages
    
    args:
        None (initialized via MongoDB connection utilities)
    
    returns:
        ConversationManager: Instance for managing conversations
    """
    
    def __init__(self):
        """
        Description: Initialize the conversation manager with MongoDB connection and indexes
        
        args:
            None
        
        returns:
            None
        """
        self.client = get_mongodb_client()
        self.db = get_database()
        self.collection = get_collection()
        
        # Create index for efficient querying
        try:
            self.collection.create_index([("user_id", 1), ("conversation_id", 1), ("updated_at", -1)])
            self.collection.create_index([("user_id", 1), ("updated_at", -1)])
        except Exception as e:
            logger.error(f"Index creation failed: {e}")

    def generate_conversation_id(self, user_id: str) -> str:
        """
        Description: Generate a new unique conversation ID using UUID
        
        args:
            user_id (str): User identifier for context
        
        returns:
            str: Unique conversation identifier
        """
        return str(uuid.uuid4())
    
    def create_conversation(self, user_id: str, conversation_id: str, title: str = None) -> Conversation:
        """
        Description: Create a new conversation document in MongoDB with optional title
        
        args:
            user_id (str): User identifier who owns the conversation
            conversation_id (str): Unique conversation identifier
            title (str): Optional conversation title, defaults to generated title if None
        
        returns:
            Conversation: Created conversation object with assigned MongoDB ID
        """
        if title is None:
            title = f"Conversation {conversation_id[:8]}"
            
        conversation = Conversation(
            title=title,
            user_id=user_id,
            conversation_id=conversation_id
        )
        
        # Insert into MongoDB - use model_dump with by_alias=True to get _id field
        conversation_dict = conversation.model_dump(by_alias=True, exclude={'id'})
        result = self.collection.insert_one(conversation_dict)
        conversation.id = str(result.inserted_id)
        
        return conversation
    
    def add_message(self, user_id: str, conversation_id: str, message: str, role: str, title: str = None) -> ConversationMessage:
        """
        Add a message to an existing conversation or create a new conversation.
        Maintains backward compatibility with the old API.
        
        :param user_id: User identifier
        :param conversation_id: Conversation identifier
        :param message: Message content (backward compatibility parameter name)
        :param role: Message role ('user' or 'assistant' - mapped to sender)
        :param title: Optional title for new conversations
        :return: ConversationMessage object
        """
        # Map role to sender for backward compatibility
        sender = "user" if role == "user" else "ai"
        
        message_obj = ConversationMessage(
            sender=sender,
            content=message,
            conversation_id=conversation_id,
            user_id=user_id if sender == 'user' else None
        )
        
        # Convert to dict for MongoDB storage using by_alias=True to get _id field
        message_dict = message_obj.model_dump(by_alias=True)
        
        # Try to update existing conversation
        update_result = self.collection.update_one(
            {"user_id": user_id, "conversation_id": conversation_id},
            {
                "$push": {"messages": message_dict},
                "$set": {"updated_at": datetime.now()}
            }
        )
        
        # If no conversation exists, create a new one
        if update_result.matched_count == 0:
            conversation = self.create_conversation(user_id, conversation_id, title)
            # Add the message to the newly created conversation
            self.collection.update_one(
                {"_id": ObjectId(conversation.id)},
                {
                    "$push": {"messages": message_dict},
                    "$set": {"updated_at": datetime.now()}
                }
            )
        
        return message_obj
    
    def get_conversation(self, user_id: str, conversation_id: str) -> Optional[Conversation]:
        """
        Retrieve a complete conversation.
        
        :param user_id: User identifier
        :param conversation_id: Conversation identifier
        :return: Conversation object or None if not found
        """
        doc = self.collection.find_one(
            {"user_id": user_id, "conversation_id": conversation_id}
        )
        
        if doc:
            # Convert ObjectId to string and rename _id to id for the model
            if '_id' in doc:
                doc['id'] = str(doc['_id'])
                del doc['_id']
            
            # Convert message _id fields to id fields
            if 'messages' in doc:
                for msg in doc['messages']:
                    if '_id' in msg:
                        msg['id'] = msg['_id']
                        del msg['_id']
            
            return Conversation(**doc)
        return None
    
    def get_conversation_history(self, user_id: str, conversation_id: str, limit: int = 10) -> List[ConversationMessage]:
        """
        Retrieve conversation history for a specific conversation.
        
        :param user_id: User identifier
        :param conversation_id: Conversation identifier
        :param limit: Maximum number of messages to retrieve (from the end)
        :return: List of ConversationMessage objects
        """
        conversation = self.get_conversation(user_id, conversation_id)
        if conversation and conversation.messages:
            # Return the last 'limit' messages
            return conversation.messages[-limit:] if len(conversation.messages) > limit else conversation.messages
        return []
    
    def get_recent_conversations(self, user_id: str, limit: int = 5) -> List[Conversation]:
        """
        Get recent conversations for a user.
        
        :param user_id: User identifier
        :param limit: Maximum number of conversations to return
        :return: List of Conversation objects
        """
        cursor = self.collection.find(
            {"user_id": user_id}
        ).sort("updated_at", -1).limit(limit)
        
        conversations = []
        for doc in cursor:
            # Convert ObjectId to string and rename _id to id for the model
            if '_id' in doc:
                doc['id'] = str(doc['_id'])
                del doc['_id']
            
            # Convert message _id fields to id fields
            if 'messages' in doc:
                for msg in doc['messages']:
                    if '_id' in msg:
                        msg['id'] = msg['_id']
                        del msg['_id']
            
            conversations.append(Conversation(**doc))
        
        return conversations
    
    def format_conversation_context(self, conversation_history: List[ConversationMessage], max_context_length: int = 2000) -> str:
        """
        Format conversation history into a context string for the LLM.
        
        :param conversation_history: List of conversation messages
        :param max_context_length: Maximum length of context string
        :return: Formatted context string
        """
        if not conversation_history:
            return ""
        
        context_parts = []
        total_length = 0
        
        # Start from the most recent messages and work backwards
        for message in reversed(conversation_history):
            logger.info(f"This is the message for conversation history :  {message}")
            role_prefix = "Assistant" if message.sender == "ai" else "User"
            # role_prefix = "Human" if message.sender == "user" else "Assistant"
            formatted_message = f"{role_prefix}: {message.content}"
            
            if total_length + len(formatted_message) > max_context_length:
                break
                
            context_parts.insert(0, formatted_message)
            total_length += len(formatted_message)
        
        return "\n".join(context_parts)
    
    def clear_conversation(self, user_id: str, conversation_id: str) -> bool:
        """
        Clear a specific conversation.
        
        :param user_id: User identifier
        :param conversation_id: Conversation identifier
        :return: True if successful
        """
        result = self.collection.delete_one(
            {"user_id": user_id, "conversation_id": conversation_id}
        )
        return result.deleted_count > 0
    
    def update_conversation_title(self, user_id: str, conversation_id: str, new_title: str) -> bool:
        """
        Update the title of a conversation.
        
        :param user_id: User identifier
        :param conversation_id: Conversation identifier
        :param new_title: New title for the conversation
        :return: True if successful
        """
        result = self.collection.update_one(
            {"user_id": user_id, "conversation_id": conversation_id},
            {
                "$set": {
                    "title": new_title,
                    "updated_at": datetime.now()
                }
            }
        )
        return result.modified_count > 0 