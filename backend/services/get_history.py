from typing import List, Optional, Dict, Any, Union
from fastapi import HTTPException, status
from backend.models.chat import ChatMessage, ChatResponse, ChatSession
from backend.database.mongodb import MongoDB
from datetime import datetime
from bson import ObjectId
import logging

class GetContext:
     
    def __init__(self):
        self.sessions_collection = "chats"
        self.messages_collection = "chat_messages"

    def _serialize_datetime(self, obj: Any) -> Any:
        """Recursively convert datetime objects to ISO format strings"""
        if isinstance(obj, dict):
            return {key: self._serialize_datetime(value) for key, value in obj.items()}
        elif isinstance(obj, list):
            return [self._serialize_datetime(item) for item in obj]
        elif isinstance(obj, datetime):
            return obj.isoformat()
        return obj
    
    def _deserialize_datetime(self, obj: Any) -> Any:
        """Recursively convert ISO format strings back to datetime objects"""
        if isinstance(obj, dict):
            return {key: self._deserialize_datetime(value) for key, value in obj.items()}
        elif isinstance(obj, list):
            return [self._deserialize_datetime(item) for item in obj]
        elif isinstance(obj, str) and 'T' in obj:
            try:
                return datetime.fromisoformat(obj)
            except ValueError:
                return obj
        return obj

    async def get_user_sessions(self, user_id: str) -> List[ChatSession]:
        try:
            sessions = await MongoDB.get_collection(self.sessions_collection)
            cursor = sessions.find({"user_id": user_id}).sort("timestamp", -1)
            
            user_sessions = []
            async for session in cursor:
                # Deserialize datetime objects from the stored session
                deserialized_session = self._deserialize_datetime(session)
                user_sessions.append(ChatSession(**deserialized_session))
            
            return user_sessions

        except Exception as e:
            logging.error(f"Failed to get user sessions: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to fetch chat sessions"
            )

    async def get_session_context(self, session_id: str, user_id: str,n:int=6) -> str:
        try:
            sessions = await MongoDB.get_collection(self.sessions_collection)
            session = await sessions.find_one({
                "id": session_id,
                "user_id": user_id
            })

            if not session:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Chat session not found session context"
                )

            # Deserialize datetime objects from the stored messages
            deserialized_session = self._deserialize_datetime(session)

            # Extract the messages and take the last 6
            messages = deserialized_session.get("messages", [])
            last_messages = messages[-n:]

            # Convert to ChatMessage objects and build context_str
            chat_messages = [ChatMessage(**msg) for msg in last_messages]
            context_str = "\n".join(
                            f"{'User Question ' if i % 2 == 0 else 'Bot Response '}: {msg.text}"
                            for i, msg in enumerate(chat_messages)
                        )
           
            
            return context_str

        except HTTPException:
            raise
        except Exception as e:
            logging.error(f"Failed to get session messages: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to fetch session messages"
            )
        
getContext=GetContext()