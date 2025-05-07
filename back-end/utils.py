import base64
import json
import struct

# def resetb64():
#     file = open("b64audio.txt", "w")
#     file.write("")
#     file.close()
    
# def reset_logs(filename):
#     file = open(filename, "w")
#     file.write("")
#     file.close()

# def log(text, filename):
#      with open(filename, "a") as file:
#         if isinstance(text, dict):
#             text = json.dumps(text, indent=2)
#         if not isinstance(text, str):
#             text = str(text)
#         file.write(text + '\n')

# def record_audio(text):
#     with open("b64audio.txt", "a") as file:
#         if not isinstance(text, str):
#             text = str(text)
#         file.write(text + '\n')
        
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