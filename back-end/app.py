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

def log(text):
     with open("server_logs.txt", "a") as file:
        if not isinstance(text, str):
            text = str(text)
        file.write(text + '\n')
    
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger("websocket-audio")
app = FastAPI()

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
        connection_id = str(uuid.uuid4())
        websocket.connection_id = connection_id
        #transcriber = OpenAITranscriber()
        try:
            while True:
                # Receive data from client
                data = await websocket.receive_json()  
                log(data)
                print(data)
                if(data['event_type'] == 'audio_response_transmitting'):
                    for client in connected_clients:
                        try:
                            await client.send_json(data)
                            print("Sent to client")
                            logger.info(f"Received message: {data}...")
                        except Exception as e:
                            logger.warning(e)
                            disconnected_clients.add(client)
                    # Remove any clients that failed
                    connected_clients.difference_update(disconnected_clients)
                # elif(data['event_type'] == 'audio_input_transmitting'):
                #     event_data = data['event_data']
                    #transcriber.send_audio_to_openai(event_data)
                # try:
                #     # Parse the JSON data
                #     json_data = json.loads(data)
                    
                #     # Check message type
                #     if "type" in json_data:
                #         if json_data["type"] == "audio_data":
                #             # Extract audio data
                #             format_type = json_data.get("format", "unknown")
                #             base64_data = json_data.get("data", "")
                            
                #             logger.info(f"Received audio chunk in {format_type} format, size: {len(base64_data)} chars")
                            
                #             # Start transcription if not already started
                #             if connection_id in active_transcribers and not hasattr(active_transcribers[connection_id], 'started'):
                #                 active_transcribers[connection_id].started = True
                #                 success = active_transcribers[connection_id].start_transcription()
                #                 if success:
                #                     logger.info("Transcription started")
                #                 else:
                #                     logger.error("Failed to start transcription")
                            
                #             # Forward the received audio data back to the client
                #             await websocket.send_text(json.dumps({
                #                 "type": "audio_response",
                #                 "audio_data": base64_data,
                #                 "message": f"Echoing audio data of {len(base64_data)} chars",
                #                 "timestamp": time.time()
                #             }))
                            
                #         elif json_data["type"] == "command" and json_data.get("command") == "stop":
                #             logger.info("Received stop command")
                            
                #             # Stop transcription if active
                #             if connection_id in active_transcribers:
                #                 active_transcribers[connection_id].stop_transcription()
                #                 del active_transcribers[connection_id]
                #                 logger.info(f"Transcription stopped for connection {connection_id}")
                            
                #             await websocket.send_text(json.dumps({
                #                 "status": "complete",
                #                 "message": "Recording stopped",
                #                 "timestamp": time.time()
                #             }))
                #     else:
                #         # Simply echo back any other message
                #         logger.info("Received non-typed message, echoing back")
                #         await websocket.send_text(data)
                        
                # except json.JSONDecodeError:
                #     logger.warning("Received non-JSON data")
                #     await websocket.send_text(data)  # Echo back the raw data
                    
        except Exception as e:
            logger.error(f"WebSocket error: {str(e)}")
            log(f"WebSocket error: {str(e)}")
        finally:
            connected_clients.discard(websocket)
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