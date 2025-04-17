import sounddevice as sd
import numpy as np
import struct
import base64

audio_chunks_encoded = []

def float_to_16bit_pcm(float32_array):
    clipped = [max(-1.0, min(1.0, x)) for x in float32_array]
    pcm16 = b''.join(struct.pack('<h', int(x * 32767)) for x in clipped)
    return pcm16

def base64_encode_audio(float32_array):
    pcm_bytes = float_to_16bit_pcm(float32_array)
    encoded = base64.b64encode(pcm_bytes).decode('ascii')
    return encoded

def base64_decode_audio(encoded_str):
    pcm_bytes = base64.b64decode(encoded_str)
    int16_array = np.frombuffer(pcm_bytes, dtype=np.int16)
    float32_array = int16_array.astype(np.float32) / 32767.0
    return float32_array

def amplify_audio(audio_data, gain=3.0):
    """Amplify audio by multiplying by gain factor and clipping to prevent distortion"""
    amplified = audio_data * gain
    # Clipping is handled by the caller functions
    return amplified

def play_audio(float32_array, samplerate=24000):
    float32_array = np.clip(float32_array, -1.0, 1.0)
    sd.play(float32_array, samplerate)
    sd.wait()

def process_audio_chunk(indata, frames, time, status):
    if status:
        print("Status:", status)
    
    audio_chunk = indata[:, 0]  # if mono, or pick a single channel
    
    # Apply amplification here
    amplified_chunk = amplify_audio(audio_chunk)
    
    encoded = base64_encode_audio(amplified_chunk)
    audio_chunks_encoded.append(encoded)
    
    print("Captured chunk:", len(audio_chunks_encoded))

if __name__ == "__main__":
    # Set amplification factor here (adjust as needed)
    gain_factor = 3.0  # 3x amplification
    
    samplerate = 24000
    channels = 1
    record_seconds = 5  # Change duration here
    
    num_blocks = int((samplerate * record_seconds) / 1024)
    
    with sd.InputStream(callback=process_audio_chunk,
                        device=1,
                        channels=channels,
                        samplerate=samplerate,
                        blocksize=1024):
        print(f"Recording for {record_seconds} seconds (with {gain_factor}x amplification)...")
        for _ in range(num_blocks):
            sd.sleep(int(1024 / samplerate * 1000))  # sleep for one block duration
    
    print("Recording done. Reconstructing audio...")
    
    # Decode all chunks and concatenate
    decoded_chunks = [base64_decode_audio(chunk) for chunk in audio_chunks_encoded]
    full_audio = np.concatenate(decoded_chunks)
    
    print("Playing back recorded audio...")
    play_audio(full_audio, samplerate)
    print("Done.")