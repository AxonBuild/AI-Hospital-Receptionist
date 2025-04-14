import sounddevice as sd
import numpy as np
import json
import configparser
import websocket

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

    def on_message(ws, message):
        data = json.loads(message)
        print("Received event:", json.dumps(data, indent=2))

    ws = websocket.WebSocketApp(
        url,
        header=headers,
        on_open=on_open,
        on_message=on_message,
    )

    ws.run_forever()
        
if __name__ == "__main__":
    response = create_session('credentials.ini', 'open_ai', 'api_key')
    print(response)
    if response != None:
        json_response = response.json()
        print(json_response)
        # Session details
        SESSION_ID = json_response["session"]["id"]
        CLIENT_SECRET = json_response["session"]["client_secret"]["value"]
        #with async websockets.connect()
        