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
import soundfile as sf
from reconstruct_audio import reconstruct_audio
from rag import rag, rag2
import ssl
from threading import Lock

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
    
def log(text):
    with open("logs.txt", "a") as file:
        try:
            if not isinstance(text, str):
                text = str(text)
            file.write(text + '\n')
        except:
            print(f"Error logging {text}")
class OpenAITranscriber:
    def __init__(self, client_websocket):
        self.client_websocket = client_websocket
        self.openai_ws = None
        self.stream_active = False
        self.audio_thread = None
        self.sent_audio = False
        self.current_audio = []
        self.sent_rag = False
        self._ws_lock = Lock()
        # Initialize logging
        file = open("logs.txt", "w")
        file.write("")
        file.close()
        
        load_dotenv()
        self.initialize_websockets()
    
    async def test(self):
        message = json.dumps({
            "event_type": "connection_established",
            "event_data": "ready"
        })
        await self.client_websocket.send_json(message)
    def is_openai_connected(self):
        return (self.openai_ws and hasattr(self.openai_ws, 'sock') 
            and self.openai_ws.sock and self.openai_ws.sock.connected)
        
    def initialize_websockets(self):
        try:
            OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
            if not OPENAI_API_KEY:
                raise ValueError("Missing OPENAI_API_KEY")
            
            headers = ["Authorization: Bearer " + OPENAI_API_KEY, "OpenAI-Beta: realtime=v1"]
            
            self.openai_ws = websocket.WebSocketApp(
                "wss://api.openai.com/v1/realtime?model=gpt-4o-mini-realtime-preview",
                header=headers,
                on_open=self.on_openai_open,
                on_message=self.on_openai_message,
                on_error=self.on_error,
                on_close=self.on_openai_close
            )
            
            self.openai_thread = threading.Thread(
                target=self.openai_ws.run_forever,
                daemon=True
            )
            self.openai_thread.start()
            time.sleep(1)  # Give time for connection
        except Exception as e:
            print(f"WebSocket initialization failed: {e}")
            log(f"WebSocket initialization failed: {e}")    
        # Add these new methods for better connection management
    def on_openai_close(self, ws, close_status_code, close_msg):
        print(f"OpenAI WebSocket closed: {close_status_code} - {close_msg}")
        log(f"OpenAI WebSocket closed: {close_status_code} - {close_msg}")
        
    def on_client_close(self, ws, close_status_code, close_msg):
        print(f"Client WebSocket closed: {close_status_code} - {close_msg}")
        log(f"Client WebSocket closed: {close_status_code} - {close_msg}")
        
    def on_client_open(self, ws):
        print("Client WebSocket connection established")
        log("Client WebSocket connection established")
    

    def set_client_websocket(self, client_websocket):
        self.client_websocket = client_websocket
        
    def process_audio_chunk(self, indata, frames, time, status):
        if status:
            print("Status:", status)
            log("Status:" + str(status))
        if not self.stream_active or self.openai_ws is None:
            return
            
        audio_chunk = indata[:, 0]  # if mono, or pick a single channel
        amplified_chunk = amplify_audio(audio_chunk)
            
        self.send_audio_to_openai(amplified_chunk)
    
    def send_audio_to_openai(self, base64_audio):
        with self._ws_lock:
            try:
                if not self.is_openai_connected():
                    print("OpenAI socket not connected, cannot send audio")
                    return False

                event = {
                    "type": "input_audio_buffer.append",
                    "audio": base64_audio
                }
                self.openai_ws.send(json.dumps(event))
                return True
                
            except Exception as e:
                print(f"Error sending audio to OpenAI: {str(e)}")
                log(f"Error sending audio to OpenAI: {str(e)}")
                return False
                            
    def on_openai_open(self, ws):
        print("Connected to OpenAI server.")
        log("Connected to OpenAI server.")
        #self.stream_active = True
        #self.start_audio_stream()
    
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
                log("Streaming... Press Ctrl+C to stop.")
                while self.stream_active:
                    sd.sleep(100)  # Just keep the stream alive
                print("Audio streaming stopped")
                log("Audio streaming stopped")
                
        self.audio_thread = threading.Thread(target=audio_stream_thread)
        self.audio_thread.daemon = True
        self.audio_thread.start()
    
    def websocket_working(self, socket_name):
        if(socket_name == "client"):
            return self.client_websocket is not None and self.client_websocket.sock is not None and self.client_websocket.sock.connected
        elif(socket_name == "openai"):
            return self.openai_ws is not None and self.openai_ws.sock is not None and self.openai_ws.sock.connected
        
    def on_openai_message(self, ws, message):
        print("Raw message received from OpenAI")
        log("Raw message received from OpenAI")
        data = json.loads(message)
        # # Forward the message to the client
        # if self.client_websocket:
        #     try:
        #         self.client_websocket.send(json.dumps(data))
        #     except Exception as e:
        #         print(f"Error sending to client: {e}")
        print(data)
        log(data)
         # Create event loop if none exists
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        if(data['type'] == "session.created"):
            event = {
                "type": "session.update",
                "session": {
                    "instructions": "If you are given base64 encoded audio, you are a tool for transcription only, otherwise you are a helpful assistant for Greenview Medical Centre"
                }
            }
            if(self.websocket_working("openai")):
                self.openai_ws.send(json.dumps(event))
            
        elif(data['type'] == "session.updated" and self.sent_audio == False):    
            pass
            # files = [
            # './sound2.wav'
            # ]
            # for filename in files:
            #     data, samplerate = sf.read(filename, dtype='float32')  
            #     channel_data = data[:, 0] if data.ndim > 1 else data
            #     base64_chunk = base64_encode_audio(channel_data)
                
            #     # Send the client event
            #     event = {
            #         "type": "input_audio_buffer.append",
            #         "audio": base64_chunk
            #     }
            
            #     time.sleep(2.5)
            #     if(self.websocket_working("openai")):
            #         self.openai_ws.send(json.dumps(event))
            #         self.sent_audio = True

        # elif(data['type'] == "session.updated" and self.sent_audio == True):
        #     response = requests.get("http://0.0.0.0:8000/get_rag_answer")
        #     if(response.status_code == 200):
        #         text = response.text
        #     event_id = data['event_id']
        #     text_message = {
        #     "event_id": event_id,
        #     "type": "conversation.item.create",
        #     "item": {
        #     "type": "message",
        #     "role": "user",
        #     "content": [{"type": "input_text", "text": text}]
        #     }
        #     }
        #     time.sleep(2.5)
        #     if(self.websocket_working("openai")):
        #         self.openai_ws.send(json.dumps(text_message))
        
        elif(data['type'] == "response.done"):
            try:
                if(data.get("response", {}).get("metadata", {}).get("topic") == "rag"):
                    print("Rag found: ", data)
                    log("Rag found: " + json.dumps(data))
                    rag_response = data['response']['output'][0]['content'][0]['text']
                    print("Rag response: ", rag_response)
                    log("Rag response: " + str(rag_response))
                    event_id = data['event_id']
                    text_message = {
                    "event_id": event_id,
                    "type": "conversation.item.create",
                    "item": {
                    "type": "message",
                    "role": "user",
                    "content": [{"type": "input_text", "text": rag_response}]
                    }
                    }
                    time.sleep(2.5)
                    if(self.websocket_working("openai")):
                        self.openai_ws.send(json.dumps(text_message))
                        self.sent_audio = True
            except:
                print("Error parsing json rag response")
                print(data)
                log(data)
                log("Error parsing json rag response")
        elif(data['type'] == "conversation.item.created"):
            message = {
            "event_id": data["event_id"],
            "type": "response.create"   
            }
            time.sleep(2.5)
            if(self.websocket_working("openai")):
                self.openai_ws.send(json.dumps(message))
                
        elif(data['type'] == "response.text.delta"):
            print(data)
            log(data)
            
        elif(data['type'] == "response.audio.delta"):
            print(data)
            log(data)
            self.current_audio.append(data['delta'])
            log("Data added into array")
            
        elif(data['type'] == "response.audio.done"): #and self.sent_audio == True):
            if(len(self.current_audio) >= 0):
                log("Appropriate length")
                to_send_audio = reconstruct_audio(self.current_audio)
                print(to_send_audio)
                base_64_audio = base64_encode_audio(to_send_audio) #encoding before sending
                loop.run_until_complete(self.send_to_client(base_64_audio))
                print("Message created, about to send")
                log("Message created, about to send")
                self.current_audio = []
                
                print("Message sent")
                log("Message sent")
                #self.sent_audio = False
            else:
                log("Insufficient length")
                return
        elif(data['type'] == "response.audio_transcript.done" and self.sent_audio == False and self.sent_rag == False):
            if(data['transcript']):
                message = data['transcript']
                log("Sending transcript for rag response")
                rag2(self.openai_ws, message)
                log("rag2 ran")
                self.sent_rag = True
                
        elif(data['type'] == "response.done"):
            return
        else:
            print("Received event:", json.dumps(data, indent=2) + '\n')
            log("Received event:" + json.dumps(data, indent=2) + '\n')

    def on_error(self, ws, error):
        if isinstance(error, Exception):
            error_msg = str(error)
        else:
            error_msg = error
        print("Error:", error_msg)
        log("Error:" + error_msg)
    
    async def send_to_client(self, base_64_audio):
        message = json.dumps({
                    "event_type": "audio_response_transmitting",
                    "event_data": base_64_audio
                })
        try:
            await self.client_websocket.send_json(message)    
        except Exception as e:
            print(e)
            log(str(e))
    # def start_transcription(self):
    #     load_dotenv()
    #     print("env loaded")
    #     log("env loaded")
    #     OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    #     url = "wss://api.openai.com/v1/realtime?model=gpt-4o-mini-realtime-preview"
    #     client_url = "ws://localhost:8000/ws"
        
    #     headers = [
    #         "Authorization: Bearer " + OPENAI_API_KEY,
    #         "OpenAI-Beta: realtime=v1"
    #     ]
    #     print("First websocket loaded")
    #     log("First websocket loaded")
    #     self.openai_ws = websocket.WebSocketApp(
    #         url,
    #         header=headers,
    #         on_open=lambda ws: self.on_openai_open(),
    #         on_message=lambda ws, msg: self.on_openai_message(msg),
    #         on_error=lambda ws, error: self.on_error(error)
    #     )
    #     print("Second websocket loaded")
    #     log("Second websocket loaded")
    #     self.client_websocket = websocket.WebSocketApp(
    #         url=client_url,
    #         on_open=lambda ws: print("Connected to client endpoint"),
    #         on_message=lambda ws, msg: print(f"Message from client: {msg}"),
    #         on_error=lambda ws, error: self.on_error(error),
    #         on_close=lambda ws, close_status_code, close_msg: print("Client connection closed")
    #     )
    #     # Run the WebSocket in a separate thread
    #     self.thread_ws = threading.Thread(target=self.openai_ws.run_forever)
    #     self.client_thread = threading.Thread(target=self.client_websocket.run_forever)
    #     self.thread_ws.daemon = True
    #     self.client_thread.daemon = True
    #     try:
    #         print("Before threads start")
    #         log("Before threads start")
    #         self.thread_ws.start()
    #         self.client_thread.start()
    #         print("After threads start")
    #         log("After threads start")
    #     except Exception as e:
    #         print(e)
    #         log(e) 
        
        
    def stop_transcription(self):
        self.stream_active = False
        
        if self.openai_ws:
            self.openai_ws.close()
            self.openai_ws = None
            
        # if self.client_websocket:
        #     self.client_websocket.close()
        #     self.client_websocket = None
            
        if self.audio_thread and self.audio_thread.is_alive():
            self.audio_thread.join(timeout=1.0)    
        return True
    
    def get_voice_output(self, text):
        # This function appears to be intended for requesting voice output
        # It currently just sends a session update event without using the text parameter
        event = {
            "type": "session.update"
        } 
        self.openai_ws.send(json.dumps(event))       
        
if __name__ == "__main__":
    print("Entering main function")
    log("Entering main function")
    transcriber = OpenAITranscriber()
    # Keep the main thread alive to prevent immediate exit
    try:
        print("Transcription running. Press Ctrl+C to exit...")
        log("Transcription running. Press Ctrl+C to exit...")
        while True:
            time.sleep(2.5)
    except KeyboardInterrupt:
        print("Stopping transcription...")
        log("Stopping transcription...")
        transcriber.stop_transcription()
