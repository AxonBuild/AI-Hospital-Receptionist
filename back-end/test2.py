import websocket
import json
import base64
import time

url = "ws://localhost:8000/ws"

def on_open(ws):
    time.sleep(5)
    dummy_audio = base64.b64encode(b"This is fake audio data").decode("utf-8")
    print("Formulating message")
    message = json.dumps({
        "type": "audio_data",
        "format": "audio/webm",
        "data": dummy_audio
    })
    print("Message sent")
    ws.send(message)

def on_error(ws, error):
    print("Error: ", error)

ws = websocket.WebSocketApp(
    url, 
    on_open=on_open,
    on_error=on_error
)

ws.run_forever()


