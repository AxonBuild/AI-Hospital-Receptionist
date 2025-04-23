import base64
import numpy as np
import sounddevice as sd

def base64_decode_audio(encoded_str):
    pcm_bytes = base64.b64decode(encoded_str)
    int16_array = np.frombuffer(pcm_bytes, dtype=np.int16)
    float32_array = int16_array.astype(np.float32) / 32767.0
    return float32_array

def play_audio(float32_array, samplerate=24000):
    float32_array = np.clip(float32_array, -1.0, 1.0)
    sd.play(float32_array, samplerate)
    sd.wait()

def reconstruct_audio(audio_chunks):
    decoded_chunks = []
    for chunk in audio_chunks:
        decoded_chunks.append(base64_decode_audio(chunk))
    full_audio = np.concatenate(decoded_chunks)
    play_audio(full_audio, 16000)