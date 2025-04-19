from fastapi import FastAPI, WebSocket
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import json
import base64
import logging
import time
from transcription import 

# Set up logging
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

@app.get("/")
async def get():
    logger.info("Root endpoint accessed")
    return {"message": "WebSocket Audio Server"}

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    logger.info("WebSocket connection accepted")
    
    try:
        while True:
            # Receive data from client
            data = await websocket.receive_text()
            logger.info(f"Received message: {data[:50]}...")
            
            try:
                # Parse the JSON data
                json_data = json.loads(data)
                
                # Check message type
                if "type" in json_data:
                    if json_data["type"] == "audio_data":
                        # Extract audio data
                        format_type = json_data.get("format", "unknown")
                        base64_data = json_data.get("data", "")
                        
                        logger.info(f"Received audio chunk in {format_type} format, size: {len(base64_data)} chars")
                        
                        # In a real app, you would process the audio here
                        # For this example, we're just acknowledging receipt
                        await websocket.send_text(json.dumps({
                            "status": "received",
                            "message": f"Received audio chunk ({len(base64_data)} chars)",
                            "timestamp": time.time()
                        }))
                    
                    elif json_data["type"] == "command" and json_data.get("command") == "stop":
                        logger.info("Received stop command")
                        await websocket.send_text(json.dumps({
                            "status": "complete",
                            "message": "Recording stopped",
                            "timestamp": time.time()
                        }))
                else:
                    # Legacy/direct text handling
                    logger.info("Received non-typed message")
                    await websocket.send_text(f"Message received: {data[:50]}...")
            
            except json.JSONDecodeError:
                logger.warning("Received non-JSON data")
                await websocket.send_text(f"Received non-JSON data of length {len(data)}")
                
    except Exception as e:
        logger.error(f"WebSocket error: {str(e)}")
    finally:
        logger.info("WebSocket connection closed")

if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)