import sounddevice as sd
import numpy as np
import struct
import base64

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
    
    volume_norm = np.linalg.norm(chunk) / len(chunk)

    if volume_norm < silence_threshold:
        # It's probably silence — skip
        return
    else:
    #Otherwise, process the chunk    
        base64_chunk = base64_encode_audio(chunk)
        print("Received chunk with shape:", chunk.shape)
    # event = {
    #     "type": "input_audio_buffer.append",
    #     "audio": base64_chunk 
    # }
    # ws.send(json.dumps(event))

def base64_decode_audio(encoded_str):
    # Decode base64 to raw PCM bytes
    pcm_bytes = base64.b64decode(encoded_str)
    # Convert to NumPy float32 array (normalize back from int16)
    int16_array = np.frombuffer(pcm_bytes, dtype=np.int16)
    float32_array = int16_array.astype(np.float32) / 32768.0
    return float32_array

def play_audio(float32_array, samplerate=16000):
    sd.play(float32_array, samplerate)
    sd.wait()
    
if __name__ == "__main__":
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
            sd.sleep(1000)
            
