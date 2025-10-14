from fastapi import WebSocket
from typing import List, Dict


class ConnectionManager:
    """
    Description: Manager for WebSocket connections organized by conversation ID for real-time chat functionality
    
    args:
        None (initializes with empty active connections dictionary)
    
    returns:
        ConnectionManager: Instance for managing WebSocket connections by conversation
    """
    def __init__(self):
        """
        Description: Initialize the connection manager with empty active connections dictionary
        
        args:
            None
        
        returns:
            None
        """
        self.active_connections: Dict[str, List[WebSocket]] = {}

    async def connect(self, conversation_id: str, websocket: WebSocket):
        """
        Description: Add a WebSocket connection to a conversation group for broadcasting
        
        args:
            conversation_id (str): Unique identifier for the conversation
            websocket (WebSocket): WebSocket connection to add to the conversation
        
        returns:
            None: Adds connection to the active connections dictionary
        """
        if conversation_id not in self.active_connections:
            self.active_connections[conversation_id] = []
        self.active_connections[conversation_id].append(websocket)

    def disconnect(self, conversation_id: str, websocket: WebSocket):
        """
        Description: Remove a WebSocket connection from a conversation group and cleanup empty groups
        
        args:
            conversation_id (str): Unique identifier for the conversation
            websocket (WebSocket): WebSocket connection to remove from the conversation
        
        returns:
            None: Removes connection and cleans up empty conversation groups
        """
        if conversation_id in self.active_connections:
            self.active_connections[conversation_id].remove(websocket)
            if not self.active_connections[conversation_id]:
                del self.active_connections[conversation_id]

    async def send_personal_message(self, message: dict, websocket: WebSocket):
        """
        Description: Send a personal message to a specific WebSocket connection
        
        args:
            message (dict): Message data to send as JSON
            websocket (WebSocket): Target WebSocket connection for the message
        
        returns:
            None: Sends JSON message to the specified WebSocket
        """
        await websocket.send_json(message)

    async def broadcast(self, conversation_id: str, message: dict):
        """
        Description: Broadcast a message to all WebSocket connections in a conversation group
        
        args:
            conversation_id (str): Unique identifier for the conversation
            message (dict): Message data to broadcast as JSON to all connections
        
        returns:
            None: Sends JSON message to all connections in the conversation group
        """
        if conversation_id in self.active_connections:
            for connection in self.active_connections[conversation_id]:
                await connection.send_json(message)
