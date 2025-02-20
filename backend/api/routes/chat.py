from fastapi import APIRouter, Depends, HTTPException, status, Response
from typing import List
from backend.models.chat import ChatMessage, ChatResponse, ChatSession, GetPersonaRequest
from backend.services.chat import ChatService
from backend.core.security import get_current_user, create_access_token, get_user_for_token_endpoint
from backend.core.config import settings

from pydantic import BaseModel
from typing import List, Dict, Any
import logging
from datetime import timedelta

router = APIRouter()
chat_service = ChatService()

class AskDFRequest(BaseModel):
    question: str

class SimilarQuestionRequest(BaseModel):
    question: str
    persona: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    expires_in: int  # seconds

# New endpoint for token generation - only this endpoint uses uniqueKey
@router.get("/token", response_model=TokenResponse)
async def get_token(response: Response, current_user: dict = Depends(get_user_for_token_endpoint)):
    """
    Generate JWT token from uniqueKey query parameter.
    This endpoint should be called first to get the token that will be used for subsequent API calls.
    """
    try:
        # Create JWT token
        expires_delta = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = await create_access_token(
            data={"sub": current_user["id"]},
            expires_delta=expires_delta
        )
        
        # Return token details to client
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60  # converting minutes to seconds
        }
        
    except Exception as e:
        logging.error(f"Token generation failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate token"
        )

@router.post("/sessions", response_model=ChatSession)
async def create_session(req: GetPersonaRequest, current_user: dict = Depends(get_current_user)):
    # Instead of just passing user_id, pass the entire current_user
    return await chat_service.create_session(req.module, current_user)

@router.get("/sessions", response_model=List[ChatSession])
async def get_sessions(current_user: dict = Depends(get_current_user)):
    return await chat_service.get_user_sessions(str(current_user["id"]))

@router.post("/{session_id}/send", response_model=ChatResponse)
async def send_message(
    session_id: str,
    message: ChatMessage,
    current_user: dict = Depends(get_current_user)
):
    return await chat_service.process_message(message.text, session_id, current_user)

@router.get("/{session_id}/messages", response_model=List[ChatMessage])
async def get_session_messages(
    session_id: str,
    current_user: dict = Depends(get_current_user)
):
    return await chat_service.get_session_messages(session_id, str(current_user["id"]))

@router.delete("/sessions/{session_id}", status_code=204)
async def delete_session(
    session_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Deletes a chat session and its associated messages.
    """
    try:
        # Use the chat service to delete the session
        await chat_service.delete_session(session_id, str(current_user["id"]))
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete chat session"
        )

@router.post("/{session_id}/ask_on_df/{message_id}", response_model=ChatResponse)
async def ask_on_df(
    session_id: str,
    message_id: str,
    req: AskDFRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Handles the Ask-on-DF functionality. Fetches the DataFrame from the specified
    message in the session and processes the user's query.
    """
    try:
        # Delegate to ChatService to handle the logic
        response = await chat_service.ask_on_df(
            df_question=req.question,
            session_id=session_id,
            user_id=str(current_user["id"]),
            parent_message_id=message_id
        )
        return response

    except HTTPException as e:
        # Handle expected errors (e.g., session or message not found)
        raise e
    except Exception as e:
        # Log unexpected errors
        logging.error(f"Failed to process Ask-on-DF: {e}")
        raise HTTPException(
            status_code=500,
            detail="An error occurred while processing your Ask-on-DF request."
        )