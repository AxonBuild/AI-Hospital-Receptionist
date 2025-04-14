import sounddevice as sd
import numpy as np
import json
import configparser
import websocket
import time
import base64

#made for extracting data from .ini files
def create_session(filename, section, variable):
    config = configparser.ConfigParser()
    config.read(filename)
    api_key = config[section][variable]
    
    url = "wss://api.openai.com/v1/realtime?model=gpt-4o-realtime-preview-2024-12-17"
    headers = [
        "Authorization: Bearer " + api_key,
        "OpenAI-Beta: realtime=v1"
    ]

    def on_open(ws):
        print("Connected to server.")
        start_message = {
        "type": "start",
        "audio": {
            "format": "pcm16",
            "sample_rate": 16000
            }
        }
        ws.send(json.dumps(start_message))
        
        dummy_chunk = {
        "event": "event456",
        "type": "input_audio_buffer.append",
        "data": str(base64.b64encode(b"\x00" * 3200).decode("utf-8"))  # 3200 bytes of silence
        }
        ws.send(json.dumps(dummy_chunk))
        print("Sent dummy audio chunk")
        stream_audio(ws)
        
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
            print("Received event:", json.dumps(data, indent=2))
    
    def on_error(ws, error):
        print("WebSocket error:", error)

    def on_close(ws, close_status_code, close_msg):
        print("WebSocket closed:", close_status_code, close_msg)

    ws = websocket.WebSocketApp(
        url,
        header=headers,
        on_open=on_open,
        on_message=on_message,
        on_error=on_error,
        on_close=on_close,
    )

    ws.run_forever()
    return ws

def stream_audio(ws):
    def callback(indata, frames, time, status):
        # Convert to bytes (PCM16) and base64 encode
        audio_bytes = indata[:, 0].astype(np.int16).tobytes()
        b64_audio = base64.b64encode(audio_bytes).decode("utf-8")

        # Send to OpenAI WebSocket
        ws.send(json.dumps({
            "event_id": "event_456",
            "type":"input_audio_buffer.append",
            "data": b64_audio
        }))
        
        
    # Start recording
    with sd.InputStream(samplerate=16000, channels=1, dtype='int16',
                        blocksize=3200, callback=callback):
        print("Listening... Speak now.")
        while True:
            time.sleep(0.1)  # Keep the stream alive
            
if __name__ == "__main__":
    ws = create_session('credentials.ini', 'open_ai', 'api_key')
        