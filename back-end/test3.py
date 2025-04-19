import os
import json
import websocket
import base64
import struct
import soundfile as sf
from websocket import create_connection
from dotenv import load_dotenv

load_dotenv()

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")

url = "wss://api.openai.com/v1/realtime?model=gpt-4o-realtime-preview-2024-12-17"
headers = [
    "Authorization: Bearer " + OPENAI_API_KEY,
    "OpenAI-Beta: realtime=v1"
]

def float_to_16bit_pcm(float32_array):
    clipped = [max(-1.0, min(1.0, x)) for x in float32_array]
    pcm16 = b''.join(struct.pack('<h', int(x * 32767)) for x in clipped)
    return pcm16

def base64_encode_audio(float32_array):
    pcm_bytes = float_to_16bit_pcm(float32_array)
    encoded = base64.b64encode(pcm_bytes).decode('ascii')
    return encoded

def on_open(ws):
    print("Connected to server.")

def on_message(ws, message):
    data = json.loads(message)    
    if data.get("type") == "transcript":
        print("Transcript:", data.get("text"), "(FINAL)" if data.get("is_final") else "")
    elif data.get("type") == "response":
        print("Assistant:", data.get("text"))
    elif data.get("type") == "audio_response":
        print("Got audio response event")
        #handle audio playback later
    else:
        print("Else clause running")
        print(data)
        
        if(data['type'] == "session.created"):
            event = {
                "type": "session.update",
                "session": {
                    "instructions": "You are a tool for transcription only, and nothing more. Just transcribe the audio given to you."
                }
            }
            ws.send(json.dumps(event))
            
        elif(data['type'] == "session.updated"):    
            print("Else clause entered")
            files = [
            './sound2.wav'
            ]

            for filename in files:
                data, samplerate = sf.read(filename, dtype='float32')  
                channel_data = data[:, 0] if data.ndim > 1 else data
                base64_chunk = base64_encode_audio(channel_data)
                
                # Send the client event
                event = {
                    "type": "input_audio_buffer.append",
                    "audio": base64_chunk
                }
                ws.send(json.dumps(event))
        else:
            print("Received event:", json.dumps(data, indent=2) + '\n')


ws = websocket.WebSocketApp(
    url,
    header=headers,
    on_open=on_open,
    on_message=on_message,
)

ws.run_forever()



