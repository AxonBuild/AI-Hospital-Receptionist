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
import threading
import asyncio

def amplify_audio(audio_data, gain=3.0):
    """Amplify audio by multiplying by gain factor and clipping to prevent distortion"""
    amplified = audio_data * gain
    # Clipping is handled by the caller functions
    return amplified

def float_to_16bit_pcm(float32_array):
    clipped = [max(-1.0, min(1.0, x)) for x in float32_array]
    pcm16 = b''.join(struct.pack('<h', int(x * 32767)) for x in clipped)
    return pcm16

def base64_encode_audio(float32_array):
    pcm_bytes = float_to_16bit_pcm(float32_array)
    encoded = base64.b64encode(pcm_bytes).decode('ascii')
    return encoded

class OpenAITranscriber:
    def __init__(self, client_websocket=None):
        self.client_websocket = client_websocket
        self.openai_ws = None
        self.stream_active = False
        self.audio_thread = None
        
    def set_client_websocket(self, client_websocket):
        self.client_websocket = client_websocket
        
    def process_audio_chunk(self, indata, frames, time, status):
        if status:
            print("Status:", status)
            
        if not self.stream_active or self.openai_ws is None:
            return
            
        audio_chunk = indata[:, 0]  # if mono, or pick a single channel
        amplified_chunk = amplify_audio(audio_chunk)
            
        self.send_audio_to_openai(amplified_chunk)
    
    def send_audio_to_openai(self, chunk, silence_threshold=0.01):
        # Handle the audio chunk (e.g., send over WebSocket, analyze, etc.)
        
        # volume_norm = np.linalg.norm(chunk) / len(chunk)
        # if volume_norm < silence_threshold:
        #     # It's probably silence — skip
        #     return
        # else:
        # Otherwise, process the chunk
        base64_chunk = base64_encode_audio(chunk)
        print("Sending chunk with shape:", chunk.shape)
        event = {
            "type": "input_audio_buffer.append",
            "audio": base64_chunk 
        }
        self.openai_ws.send(json.dumps(event))
    
    def on_openai_open(self):
        print("Connected to OpenAI server.")
        self.stream_active = True
        self.start_audio_stream()
    
    def start_audio_stream(self):
        def audio_stream_thread():
            samplerate = 16000  # Lower is easier to handle live
            channels = 1
            # Open a stream
            with sd.InputStream(callback=self.process_audio_chunk,
                                device=1,
                                channels=channels,
                                samplerate=samplerate,
                                blocksize=1024):  # You can tweak this size
                print("Streaming... Press Ctrl+C to stop.")
                while self.stream_active:
                    sd.sleep(100)  # Just keep the stream alive
                print("Audio streaming stopped")
                
        self.audio_thread = threading.Thread(target=audio_stream_thread)
        self.audio_thread.daemon = True
        self.audio_thread.start()
    
    def on_openai_message(self, message):
        print("Raw message received from OpenAI")
        data = json.loads(message)
        
        # Forward the message to the client
        if self.client_websocket:
            asyncio.run(self.send_to_client(data))
            
        # Process for console output
        if data.get("type") == "transcript":
            print("Transcript:", data.get("text"), "(FINAL)" if data.get("is_final") else "")
        elif data.get("type") == "response":
            print("Assistant:", data.get("text"))
        elif data.get("type") == "audio_response":
            print("Got audio response event")
            #handle audio playback later
        else:
            print("Received event:", json.dumps(data, indent=2) + '\n')
    
    async def send_to_client(self, data):
        if self.client_websocket:
            try:
                await self.client_websocket.send_text(json.dumps(data))
            except Exception as e:
                print(f"Error sending to client: {e}")
    
    def start_transcription(self):
        load_dotenv()
        
        OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
        url = "wss://api.openai.com/v1/realtime?intent=transcription"
        headers = [
            "Authorization: Bearer " + OPENAI_API_KEY,
            "OpenAI-Beta: realtime=v1"
        ]
        
        self.openai_ws = websocket.WebSocketApp(
            url,
            header=headers,
            on_open=lambda ws: self.on_openai_open(),
            on_message=lambda ws, msg: self.on_openai_message(msg),
        )
        
        # Run the WebSocket in a separate thread
        ws_thread = threading.Thread(target=self.openai_ws.run_forever)
        ws_thread.daemon = True
        ws_thread.start()
        
        return True
        
    def stop_transcription(self):
        self.stream_active = False
        
        # Close the OpenAI WebSocket connection
        if self.openai_ws:
            self.openai_ws.close()
            self.openai_ws = None
            
        # Wait for audio thread to finish
        if self.audio_thread and self.audio_thread.is_alive():
            self.audio_thread.join(timeout=1.0)
            
        return True
    
    def get_voice_output(text):
        pass
