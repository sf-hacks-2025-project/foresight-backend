from google import genai
from pydantic import BaseModel
from dotenv import load_dotenv
from google.genai import types
from modules import database
from utils.common import remove_formatting

import json
import os
import time
import random
from google.genai import errors

load_dotenv()

class Item(BaseModel):
    name: str
    description: str
    location: str
    color: str

class VisualContext(BaseModel):
    image_location: str
    description: str
    items: list[Item]

client = genai.Client(api_key=os.getenv('GEMINI_API_KEY'))

visual_context_config = types.GenerateContentConfig(
    response_schema=VisualContext,
    response_mime_type='application/json'
)

query_config = types.GenerateContentConfig(
    tools=[database.fetch_history, database.get_conversation_history],
    response_mime_type='text/plain',
    temperature=1.0
)

async def get_visual_context(picture_file):
    """Takes a photo and saves its visual context to the database."""
    if not picture_file:
        raise ValueError("Picture file is required")
    
    picture = await client.aio.files.upload(file=picture_file, config=types.UploadFileConfig(mime_type='image/png'))
    
    base_prompt = f"""
    You are an assistant for visually impaired users. Given an image of their point of view, create a detailed visual context that includes:
    
    1. A comprehensive description of the scene including:
    - The overall scene and atmosphere
    - Each object's location, color, and spatial relationship to other objects
    - Any text visible in the image
    - Important contextual details
    
    2. Structure your response as a VisualContext object with:
    - image_location: A brief description of where this image was taken
    - description: Your comprehensive scene description
    - items: A list of important objects, each with name, description, location, color, and spatial relationship
    
    Be thorough and precise, as this context will be used to answer future questions about objects seen.
    """

    response = await client.aio.models.generate_content(
        model='gemini-2.0-flash',
        contents=[base_prompt, picture],
        config=visual_context_config
    )

    visual_context = json.loads(response.text)
    return visual_context

def generate_fallback_response(query):
    """Generate a fallback response when the API is unavailable.
    
    Args:
        query: The user's query text.
        
    Returns:
        A fallback response.
    """
    # Simple keyword-based fallback responses
    if not query:
        return "I'm sorry, I couldn't process your request right now. Please try again later."
    
    query = query.lower()
    
    # Check for common question patterns
    if "where" in query:
        if any(item in query for item in ["glasses", "keys", "wallet", "phone"]):
            return "I'm sorry, I can't access my visual memory right now due to a technical issue. Please try again in a few minutes."
    
    if "hello" in query or "hi" in query:
        return "Hello! I'm having some technical difficulties right now, but I'm still here to chat."
    
    if "how are you" in query:
        return "I'm experiencing some technical limitations at the moment, but I'm still operational. How can I assist you?"
    
    if "thank" in query:
        return "You're welcome! I'm happy to help, even with my current technical limitations."
    
    # Default fallback
    return "I'm experiencing some technical difficulties accessing my full capabilities right now. Please try again in a few minutes."

async def generate_audio_transcription(audio_file=None):
    """
    Transcribes the given audio file using Google's Gemini API.
    
    Args:
        user_id: Optional user ID for tracking or logging purposes
        audio_file: Audio file to transcribe (file-like object)
        
    Returns:
        The transcribed text from the audio file
    """
    if not audio_file:
        return "No audio file provided for transcription."
    
    try:
        # Upload the audio file to Gemini
        audio_upload = await client.aio.files.upload(
            file=audio_file, 
            config=types.UploadFileConfig(mime_type='audio/mpeg')
        )
        
        # Reset the file pointer for potential future use
        audio_file.seek(0)
        
        # Create a simple prompt for transcription
        prompt = """
        Please transcribe the audio file accurately. 
        Only provide the transcription text without any additional commentary or explanation.
        """
        
        # Create the generation content
        generation_config = types.GenerateContentConfig(
            response_mime_type='text/plain',
            temperature=0.2  # Lower temperature for more accurate transcription
        )
        
        # Generate the transcription using Gemini
        response = await client.aio.models.generate_content(
            model='gemini-2.0-flash',
            contents=[prompt, audio_upload],
            config=generation_config
        )
        
        # Extract and return the transcribed text
        transcription = response.text.strip()
        return transcription
    except Exception as e:
        print(f"Error transcribing audio with Gemini: {str(e)}")
        return f"Error transcribing audio: {str(e)}"


async def generate_response(user_id, audio_file=None, text_query=None, max_retries=3):
    """Handles user questions about previously saved visual contexts.
    
    Args:
        user_id: The ID of the user.
        audio_file: Optional audio file containing the user's question.
        text_query: Optional text query from the user.
        max_retries: Maximum number of retries for API calls.
        
    Returns:
        The assistant's response as text.
    """
    if not audio_file and not text_query:
        raise ValueError("Either audio_file or text_query must be provided")
    
    files = []
    if audio_file:
        audio_upload = await client.aio.files.upload(file=audio_file, config=types.UploadFileConfig(mime_type='audio/mpeg'))
        files.append(audio_upload)
    
    base_prompt = f"""
    You are an assistant for visually impaired users. 
    A user with the user ID {user_id} has asked a question through {'audio' if audio_file else 'text'}. Your task is to:

    1. {'Listen to the audio question and provide a clear answer.' if audio_file else 'Read the text question and provide a clear answer.'}
    2. Use the get_conversation_history function to retrieve previous messages in this conversation
    3. Use the fetch_history function to get your visual context history of what you have seen for this user

    HANDLING CONTEXT AND FOLLOW-UP QUESTIONS:
    - When a user asks "What items have you seen?" - list all items from your visual contexts with their locations
    - When they follow up with questions like "Where are those items?" or "Tell me more about those items":
      * FIRST identify which items you mentioned in your PREVIOUS response (not from all visual contexts)
      * THEN provide detailed information about ONLY those specific items
      * Include exact locations, colors, and spatial relationships for each item
    - For ANY follow-up using words like "those", "them", "these", etc., ALWAYS refer to what YOU just mentioned
    - Maintain a clear mental model of which items you've told the user about in your most recent response

    ANSWERING ABOUT SPECIFIC ITEMS:
    - If asked about a specific item ("Where is my wallet?"):
      * If you've seen it, provide the exact location and when you saw it
      * If you haven't seen it, simply say "I haven't seen your wallet" without mentioning other items
    - NEVER say "I saw X but didn't see Y" - only mention items you've actually observed

    RESPONSE STYLE AND FORMAT:
    - Be direct and conversational - imagine you're speaking to the person, not writing a report
    - Avoid phrases like "Based on my visual history" or "I can help with that"
    - Don't use phrases like "The image shows" or "I can see" - speak as if you're describing what's around the person
    - Group items by location and mention the time only once per location group
      * GOOD: "The woven baskets and wire baskets were on the top shelf, and the bags were hanging on the door 31 minutes ago."
      * BAD: "The woven baskets were on the top shelf 31 minutes ago. The wire baskets were on the top shelf 31 minutes ago."
    - For questions about people, respond directly (e.g., "You're looking at a person wearing a black hat just now.")
    
    MOST IMPORTANT: When responding to a follow-up question, ALWAYS check what specific items you mentioned in your previous response and address THOSE items specifically.
    """

    contents = [base_prompt, *files]
    if text_query:
        contents.append(text_query)

    # Implement retry with exponential backoff
    retry_count = 0
    base_wait_time = 2  # Start with 2 seconds
    
    while retry_count <= max_retries:
        try:
            response = await client.aio.models.generate_content(
                model='gemini-2.0-flash',
                contents=contents,
                config=query_config
            )
            
            response_text = response.text.strip()
            response_text = remove_formatting(response_text)

            # Save the user's message to conversation history
            if text_query:
                await database.save_message(user_id, "user", text_query)
                
            # Save the assistant's response to conversation history
            await database.save_message(user_id, "assistant", response_text)
            
            return response_text

        except errors.ClientError as e:
            # Check if it's a rate limit error (429)
            if hasattr(e, 'status_code') and e.status_code == 429:
                retry_count += 1
                
                if retry_count > max_retries:
                    # If we've exceeded max retries, use a fallback response
                    fallback_response = generate_fallback_response(text_query)
                    return fallback_response
                
                # Calculate wait time with exponential backoff and jitter
                wait_time = base_wait_time * (2 ** (retry_count - 1)) + random.uniform(0, 1)
                print(f"Rate limit exceeded. Retrying in {wait_time:.2f} seconds...")
                time.sleep(wait_time)
            else:
                # For other errors, use fallback and don't retry
                fallback_response = generate_fallback_response(text_query)
                return fallback_response
        except Exception as e:
            # For any other exception, use fallback
            print(f"Error generating response: {str(e)}")
            fallback_response = generate_fallback_response(text_query)
            return fallback_response