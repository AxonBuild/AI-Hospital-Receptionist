from fastapi import FastAPI, WebSocket
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import json
import base64
import logging
import time
import asyncio
from transcription import OpenAITranscriber
from rag import rag
import uuid
import traceback
from typing import Dict
import asyncio
from dotenv import load_dotenv
import os
import requests

#LOG_FILENAME = "server_logs.txt"

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger("websocket-audio")
#reset_logs(LOG_FILENAME)

app = FastAPI()
transcriber_instances: Dict[str, OpenAITranscriber] = {}
# Enable CORS to allow requests from Next.js frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

# Store active transcribers by connection
active_transcribers = {}
connected_clients = set()
disconnected_clients = set()

@app.get("/")
async def get():
    logger.info("Root endpoint accessed")
    return {"message": "WebSocket Audio Server"}

@app.get("/getEphemeralKey")
async def get_ephemeral_key():
    load_dotenv()
    OPEN_AI_API_KEY = os.getenv("OPENAI_API_KEY")
    url = "https://api.openai.com/v1/realtime/sessions"
    headers = {
        "Authorization": f"Bearer {OPEN_AI_API_KEY}",
        "Content-Type": "application/json",
        "OpenAI-Beta": "realtime=v1"
    }
    payload = {
        "model": "gpt-4o-realtime-preview-2024-12-17",
        "voice": "verse"
    }

    response = requests.post(url, headers=headers, json=payload)
    response = response.json()
    ephemeral_key = response["client_secret"]["value"]
    return ephemeral_key

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    try:
        await websocket.accept()
        logger.info("WebSocket connection accepted")
        connected_clients.add(websocket)
        
        # Create or reuse transcriber for this connection
        connection_id = str(uuid.uuid4())
        if connection_id not in transcriber_instances:
            transcriber_instances[connection_id] = OpenAITranscriber(websocket)
            await asyncio.sleep(5)
            await transcriber_instances[connection_id].test()
            
        try:
            while True:
                data = await websocket.receive_json()  
                #log(data, LOG_FILENAME)
                #this one is actually response
                if data['event_type'] == 'audio_response_transmitting':
                    try:
                        #log("Output Data transmitting", LOG_FILENAME)
                        await websocket.send_json(data)
                        #log("Output Data transmitted", LOG_FILENAME)
                    except Exception as e:
                        logger.error(f"Failed to send to client: {e}")
                        raise  # This will trigger the outer exception handler
                elif data['event_type'] == 'audio_input_transmitting':
                    #log("Transmitting data", LOG_FILENAME)
                    if transcriber_instances[connection_id].is_openai_connected():
                        transcriber_instances[connection_id].send_audio_to_openai(data['event_data'])
                        #record_audio(data['event_data'])
                    #log("Data transmitted", LOG_FILENAME)
        except Exception as e:
            logger.error(f"WebSocket error: {str(e)}")
        finally:
            # Clean up
            connected_clients.discard(websocket)
            if connection_id in transcriber_instances:
                transcriber_instances[connection_id].stop_transcription()
                del transcriber_instances[connection_id]
            logger.info("WebSocket connection closed")
    except Exception as e:
        print(e)
        #log(e, LOG_FILENAME)
        traceback.print_exc()
        
if __name__ == "__main__":
    try:
        uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True, reload_excludes=["b64audio.txt", "logs.txt", "server_logs.txt", "saved_server_logs.txt", "saved_logs.txt", "*."])
    except Exception as e:
        print(e)
        #log(e, LOG_FILENAME)
        traceback.print_exc()
