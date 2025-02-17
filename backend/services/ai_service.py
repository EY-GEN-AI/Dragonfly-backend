
from interpreter import interpreter
from typing import Optional,List
import asyncio
from concurrent.futures import ThreadPoolExecutor
import logging
from fastapi import HTTPException, status

import os

import json
from backend.services.sahdevvv import sd
from datetime import datetime
from backend.services.custom_json import TableDataSerializer
from backend.services.summary_generator import DataframeSummary
from backend.services.prompt_next_question import PromptQuestion
from backend.services.get_history import getContext  # Import the GetContext class
from backend.database.mongodb import MongoDB



from diskcache import Cache
 
cache_dir = os.path.join(os.path.dirname(__file__), "../cache_directory")
#cache_dir = "./backend/cache_directory"
cache = Cache(cache_dir,size_limit=int(1e12),eviction_policy="none")


class AIService:
    _instance = None
    _executor = ThreadPoolExecutor(max_workers=10)
    _active_sessions = {} 

    def __init__(self):
        # Configure environment first
        self._configure_environment()
        self.sessions_collection = "chats"
     
        # Single interpreter configuration for Azure
        interpreter.reset()
        interpreter.llm.model = "azure/gpt-4"
        interpreter.llm.temperature=0.2
        interpreter.system_message += """
        Run shell commands with -y so the user doesn't have to confirm them.
        """

    def _configure_environment(self):
        """Configure environment settings for OpenAI and SSL"""
        try:
       
            
            logging.info("Configuration completed successfully")
            
        except Exception as e:
            logging.error(f"Failed to configure environment: {str(e)}")
            raise



            




    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = AIService()
        return cls._instance
    

    async def get_persona(self,session_id,current_user):
        sessions = await MongoDB.get_collection(self.sessions_collection)

            # Verify session exists and belongs to the user
        session = await sessions.find_one({"id": session_id, "user_id": str(current_user["id"])})
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Persona not found"
            )
        # Grab persona from current_user
        if session and "persona" in session:
            persona = session["persona"]
        else:
            persona = None
        print("persona is ",persona)
        return persona

    # async def get_ai_response(self, message: str, user_id: str,session_id:str) -> str:
    async def get_ai_response(self, user_message: str, user_id: str, session_id: str, current_user: dict) -> dict:
        """Get AI response asynchronously with user-isolated context"""
        try:

            persona=await self.get_persona(session_id,current_user)
            context_str=await getContext.get_session_context(user_id=user_id,session_id=session_id)
            print(f"Context string is ",context_str)
            response = await asyncio.get_event_loop().run_in_executor(
                self._executor,
                self._process_user_message,
                user_message,
                # user_id,
                # session_id,
                context_str,
                persona    # <--- pass it to the sync method
            )



            return response
        except Exception as e:
            logging.error(f"AI Service error for user {user_id}: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to generate AI response"
            )
        




        

    def _process_user_message(self, message: str,context_str:str,persona: str) -> dict:
        """Process message with user-specific interpreter context"""
        #### Cache #########

        cache_key = message
    
        # Check cache
        cached_response = cache.get(cache_key)
        if cached_response:
            print("Cache hit!")
            return cached_response
    
        print("Cache miss! Processing...")
        prompt_question_object=PromptQuestion
        print("*"*80)
        print(context_str)
        print("*"*80)

        print("Suggested next question : ",prompt_question_object.get_similar_question(message,persona))
        next_question=prompt_question_object.get_similar_question(message,persona)

        print("Got history")

        try:
            
            extracted_sql,df,msg = sd.execute_query_with_retries(message,context_str)

            print(df.head())
            
            if not df.empty:
                # Convert DataFrame to dict for JSON serialization
                df.to_csv("temp.csv")
                tds=TableDataSerializer
                df_dict = df.to_dict('records')
                df_dict_serialized = tds.serialize_records(df_dict)
                df_columns = df.columns.tolist()
                summary_object=DataframeSummary(df)
                summary=summary_object.generate_summary(question=message)
                ai_response = {
                    'type': 'sql_response',
                    'content': extracted_sql,
                    'data': {
                        'records': df_dict_serialized,
                        'columns': df_columns
                    },
                    'summary':summary,
                    'next_question':next_question
                }
                

            else:
                ai_response = {
                    'type': 'text',
                    'content': msg,
                    'next_question': next_question
                }

            #self._save_chat_interaction(user_id, message, ai_response['content'])
            cache.set(cache_key, ai_response, expire=None)
            return ai_response

        except Exception as e:
            logging.error(f"Chat processing error: {e}")
            stringgg=sd.generate_fallback_response(message,"",context_str)
            return {
                'type': 'text',
               'content':stringgg,
               'next_question':next_question
            }