import requests
import configparser

#made for extracting data from .ini files
def create_session(filename, section, variable):
    config = configparser.ConfigParser()
    config.read(filename)
    api_key = config[section][variable]
    
    url = "https://api.openai.com/v1/realtime/sessions"
    headers = {
    "Authorization": f"Bearer {api_key}",  
    "Content-Type": "application/json"
    }
    data = {
    "model": "gpt-4o-realtime-preview",
    "modalities": ["audio", "text"],
    "instructions": "You are a friendly assistant."
    }
    
    response = requests.post(url, headers = headers, json = data)
    if(response.status_code == 200):
        return True
    else 
        return False


if __name__ == "__main__":
    create_session('credentials.ini', 'open_ai', 'api_key')
