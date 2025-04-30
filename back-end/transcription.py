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
        if not isinstance(text, str):
            text = str(text)
        file.write(text + '\n')
class OpenAITranscriber:
    def __init__(self):
        self.client_websocket = None
        self.client_thread = None
        self.openai_ws = None
        self.thread_ws = None
        self.stream_active = False
        self.audio_thread = None
        self.sent_audio = False
        self.current_audio = None
        file = open("logs.txt", "w")
        file.write("")
        file.close()
        load_dotenv()
        print("env loaded")
        log("env loaded")
        OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
        url = "wss://api.openai.com/v1/realtime?model=gpt-4o-mini-realtime-preview"
        client_url = "ws://localhost:8000/ws"
        
        headers = [
            "Authorization: Bearer " + OPENAI_API_KEY,
            "OpenAI-Beta: realtime=v1"
        ]
        print("First websocket loaded")
        log("First websocket loaded")
        self.openai_ws = websocket.WebSocketApp(
            url,
            header=headers,
            on_open=lambda ws: self.on_openai_open(),
            on_message=lambda ws, msg: self.on_openai_message(msg),
            on_error=lambda ws, error: self.on_error(error)
        )
        print("Second websocket loaded")
        log("Second websocket loaded")
        self.client_websocket = websocket.WebSocketApp(
            url=client_url,
            on_open=lambda ws: print("Connected to client endpoint"),
            on_message=lambda ws, msg: print(f"Message from client: {msg}"),
            on_error=lambda ws, error: self.on_error(error),
            on_close=lambda ws, close_status_code, close_msg: print("Client connection closed")
        )
        # Run the WebSocket in a separate thread
        #temporary turning off of ssl certificate verification
        self.thread_ws = threading.Thread(target=self.openai_ws.run_forever)
        self.client_thread = threading.Thread(target=self.client_websocket.run_forever)
        self.thread_ws.daemon = True
        self.client_thread.daemon = True
        try:
            print("Before threads start")
            log("Before threads start")
            self.thread_ws.start()
            self.client_thread.start()
            print("After threads start")
            log("After threads start")
        except Exception as e:
            print(e)
            log(e)
        

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
    
    def send_audio_to_openai(self, chunk, silence_threshold=0.01):
        # Handle the audio chunk (e.g., send over WebSocket, analyze, etc.)
        
        # volume_norm = np.linalg.norm(chunk) / len(chunk)
        # if volume_norm < silence_threshold:
        #     # It's probably silence — skip
        #     return
        # else:
        # Otherwise, process the chunk
        print("Sending chunk with shape:", chunk.shape)
        log("Sending chunk with shape:" + str(chunk.shape))
        event = {
            "type": "input_audio_buffer.append",
            "audio": chunk 
        }
        if(self.openai_ws is not None and self.openai_ws.sock is not None and self.openai_ws.sock.connected):
            self.openai_ws.send(json.dumps(event))     
        else:
            print("OpenAI socket closed")
            log("OpenAI socket closed")
    def on_openai_open(self):
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
        
    def on_openai_message(self, message):
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
        
        if(data['type'] == "session.created"):
            rag2(self.openai_ws, "Where is greenview hospital located?")
            # event = {
            #     "type": "session.update",
            #     "session": {
            #         "instructions": "If you are given base64 encoded audio, you are a tool for transcription only, otherwise you are a helpful assistant for Greenview Medical Centre"
            #     }
            # }
            # if(self.websocket_working("openai")):
            #     self.openai_ws.send(json.dumps(event))
            
        elif(data['type'] == "session.updated" and self.sent_audio == False):    
            print("Else clause entered")
            log("Else clause entered")
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
                time.sleep(1)
                if(self.websocket_working("openai")):
                    self.openai_ws.send(json.dumps(event))
                    self.sent_audio = True

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
        #     time.sleep(1)
        #     if(self.websocket_working("openai")):
        #         self.openai_ws.send(json.dumps(text_message))
        elif(data['type'] == "response.done" and data.get("response", {}).get("metadata", {}).get("topic") == "rag"):
            print("Rag found: " ,data)
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
            time.sleep(1)
            if(self.websocket_working("openai")):
                self.openai_ws.send(json.dumps(text_message))
                self.sent_audio = True
        elif(data['type'] == "response.done"):
            print(data)
            log(data)
        elif(data['type'] == "conversation.item.created"):
            message = {
            "event_id": data["event_id"],
            "type": "response.create"   
            }
            self.current_audio = []
            time.sleep(1)
            if(self.websocket_working("openai")):
                self.openai_ws.send(json.dumps(message))
                
        elif(data['type'] == "response.text.delta"):
            print(data)
            log(data)
            
        elif(data['type'] == "response.audio.delta" and self.sent_audio == True):
            print(data)
            log(data)
            self.current_audio.append(data['delta'])
            
        elif(data['type'] == "response.audio.done" and self.sent_audio == True):
            if(len(self.current_audio) >= 0):
                to_send_audio = reconstruct_audio(self.current_audio)
                print(to_send_audio)
                base_64_audio = base64_encode_audio(to_send_audio) #encoding before sending
                message = json.dumps({
                    "event_type": "audio_response_transmitting",
                    "event_data": base_64_audio
                })
                print("Message created, about to send")
                log("Message created, about to send")
                if(self.websocket_working("client")):#self.client_websocket is not None and self.client_websocket.sock is not None and self.client_websocket.sock.connected):
                    self.client_websocket.send(message)    
                print("Message sent")
                log("Message sent")
                #self.sent_audio = False
            else:
                return
        elif(data['type'] == "response.audio_transcript.done" and self.sent_audio == False):
            if(data['transcript']):
                message = data['transcript']
                self.transcript_websocket.send(message)
                log("Sending transcript for rag response")
                rag2(message)
                
        elif(data['type'] == "response.done"):
            return
        else:
            print("Received event:", json.dumps(data, indent=2) + '\n')
            log("Received event:" + json.dumps(data, indent=2) + '\n')

    def on_error(self, error):
        print("Error:", error)
        log("Error:" + error)
    
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
        
        # Close the OpenAI WebSocket connection
        if self.openai_ws:
            self.openai_ws.close()
            self.openai_ws = None
            
        # Wait for audio thread to finish
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
            time.sleep(1)
    except KeyboardInterrupt:
        print("Stopping transcription...")
        log("Stopping transcription...")
        transcriber.stop_transcription()