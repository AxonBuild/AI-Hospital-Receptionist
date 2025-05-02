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

def resetb64():
    file = open("b64audio.txt", "w")
    file.write("")
    file.close()
    
def reset_logs():
    file = open("server_logs.txt", "w")
    file.write("")
    file.close()

def log(text):
     with open("server_logs.txt", "a") as file:
        if isinstance(text, dict):
            text = json.dumps(text, indent=2)
        if not isinstance(text, str):
            text = str(text)
        file.write(text + '\n')

def record_audio(text):
    with open("b64audio.txt", "a") as file:
        if not isinstance(text, str):
            text = str(text)
        file.write(text + '\n')

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger("websocket-audio")
reset_logs()

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
                log(data)
                #this one is actually response
                if data['event_type'] == 'audio_response_transmitting':
                    try:
                        log("Output Data transmitting")
                        await websocket.send_json(data)
                        log("Output Data transmitted")
                    except Exception as e:
                        logger.error(f"Failed to send to client: {e}")
                        raise  # This will trigger the outer exception handler
                elif data['event_type'] == 'audio_input_transmitting':
                    log("Transmitting data")
                    if transcriber_instances[connection_id].is_openai_connected():
                        transcriber_instances[connection_id].send_audio_to_openai(data['event_data'])
                        record_audio(data['event_data'])
                    log("Data transmitted")    
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
        log(e)
        traceback.print_exc()
        
if __name__ == "__main__":
    try:
        uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
    except Exception as e:
        print(e)
        log(e)
        traceback.print_exc()
