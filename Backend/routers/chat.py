"""Chat router for HR AI assistant and Student AI assistant"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from database.postgres import get_db
from database.models import User
from schemas.api import ChatMessageRequest, ChatMessageResponse
from services.chat_engine import ChatOrchestrator, StudentChatOrchestrator
from auth.dependencies import get_current_active_user

router = APIRouter(prefix="/api/v1/chat", tags=["Chat"])


@router.post("/message", response_model=ChatMessageResponse)
async def chat_message(
    request: ChatMessageRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Process a chat message and return AI response
    
    Accessible to recruiters, admins, and students
    """
    try:
        # Route based on user role
        if current_user.role.value == "student":
            # Initialize student chat orchestrator
            orchestrator = StudentChatOrchestrator(db, current_user.id)
            
            # Process message
            response_text, data = orchestrator.process_message(request.message)
            
            return ChatMessageResponse(
                response=response_text,
                data=data,
                conversation_id=request.conversation_id
            )
        elif current_user.role.value in ["recruiter", "admin", "tpo"]:
            # Initialize HR chat orchestrator
            orchestrator = ChatOrchestrator(db)
            
            # Process message
            response_text, data = orchestrator.process_message(request.message)
            
            return ChatMessageResponse(
                response=response_text,
                data=data,
                conversation_id=request.conversation_id
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Chat feature is only available for students, recruiters, admins, and TPOs"
            )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing chat message: {str(e)}"
        )
