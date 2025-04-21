import sounddevice as sd
import numpy as np
import json
import configparser
import websocket
import time
import base64
import requests
import os
import struct
from dotenv import load_dotenv

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
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

def process_audio_chunk(indata, frames, time, status):
    if status:
        print("Status:", status)

    # `indata` is a NumPy array of shape (frames, channels)
    audio_chunk = np.frombuffer(indata, dtype=np.int16).astype(np.float32) / 32768.0
    my_stream_function(audio_chunk)

def my_stream_function(chunk, silence_threshold = 0.01):
    # Handle the audio chunk (e.g., send over WebSocket, analyze, etc.)
    
    # volume_norm = np.linalg.norm(chunk) / len(chunk)

    # if volume_norm < silence_threshold:
    #     # It's probably silence — skip
    #     return
    # else:
    # Otherwise, process the chunk    
    base64_chunk = base64_encode_audio(chunk)
    print("Received chunk with shape:", chunk.shape)
    event = {
        "type": "input_audio_buffer.append",
        "audio": base64_chunk 
    }
    ws.send(json.dumps(event))
    

def on_open(ws):
    print("Connected to server.")
    

def on_message(ws, message):
    print("Raw message received")
    data = json.loads(message)
    print(data)
    if data.get("type") == "transcript":
        print("Transcript:", data.get("text"), "(FINAL)" if data.get("is_final") else "")
    elif data.get("type") == "response":
        print("Assistant:", data.get("text"))
    elif data.get("type") == "audio_response":
        print("Got audio response event")
        #handle audio playback later
    else:
        print("Received event:", json.dumps(data, indent=2) + '\n')
        if(data['type'] == 'session.created'):
            event = {
                "type": "session.update",
                "session": {
                    "instructions": "Your job is to provide a transcript of the provided audio and nothing else. You are just a tool for transcription."
                }
            }
            ws.send(json.dumps(event))
        elif(data['type'] == 'session.updated'):
            # Parameters
            samplerate = 16000  # Lower is easier to handle live
            channels = 1
            # Open a stream
            with sd.RawInputStream(callback=process_audio_chunk,
                                device=1,
                                channels=channels,
                                samplerate=samplerate,
                                blocksize=1024):  # You can tweak this size
                print("Streaming... Press Ctrl+C to stop.")
                while True:
                    sd.sleep(1000)  # Just keep the stream alive
        print("Received event:", json.dumps(data, indent=2))


ws = websocket.WebSocketApp(
        url,
        header=headers,
        on_open=on_open,
        on_message=on_message,
    )

ws.run_forever()


















































































































