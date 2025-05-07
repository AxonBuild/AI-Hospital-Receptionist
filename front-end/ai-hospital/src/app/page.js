"use client";
import { useEffect, useRef, useState } from "react";
import Image from "next/image";
import styles from "./page.module.css";

export default function Home() {
  const [isRecording, setIsRecording] = useState(false);
  const [logMessages, setLogMessages] = useState([]);
  const [connectionReady, setConnectionReady] = useState(false);

  const dataRef = useRef(null);
  const summaryRef = useRef(null);
  const audioRef = useRef(null);
  const mediaRecorderRef = useRef(null);
  const socketRef = useRef(null);
  const audioContextRef = useRef(null);
  const sourceNodeRef = useRef(null);
  const processorRef = useRef(null);
  const nodesConnectedRef = useRef(false);
  
  // Audio queue and playback state
  const audioQueueRef = useRef([]);
  const isPlayingRef = useRef(false);

  const log = (message) => {
    console.log(`[${new Date().toLocaleTimeString()}] ${message}`);
    setLogMessages(prev => [...prev, `[${new Date().toLocaleTimeString()}] ${message}`]);
  };

  useEffect(() => {
    if (!socketRef.current || socketRef.current.readyState !== WebSocket.OPEN) {
      //socketRef.current = new WebSocket('ws://localhost:8000/ws');
      socketRef.current = new WebSocket('wss://ai-hospital-receptionist-esz6.vercel.app/ws');
      socketRef.current.onmessage = (event) => {
        log(`Received WebSocket message: ${event.data.substring(0, 50)}...`);
        try {
          const data = JSON.parse(event.data);
          log(`Parsed data: ${JSON.stringify(data, null, 2)}`);

          if (data.event_type === "checking connectivity" && data.event_data === "connection established") {
            setConnectionReady(true);
            log("Server connection confirmed - ready to record");
          }

          if (data.event_type === "audio_response_transmitting") {
            handleAudioResponse(data.event_data);
          }
        } catch (e) {
          log(`Error handling message: ${e.message}`);
        }
      };

      socketRef.current.onerror = (error) => {
        log(`WebSocket error: ${error.message || "Unknown error"}`);
      };

      socketRef.current.onclose = (event) => {
        log(`WebSocket closed: ${event.code} ${event.reason}`);
      };

      log("WebSocket initialized - waiting for confirmation");
    }

    return () => {
      if (socketRef.current) {
        socketRef.current.close();
        log("WebSocket connection closed");
      }
    };
  }, []);

  useEffect(() => {
    let h2text = document.querySelector("#instruction");
    h2text?.classList.add("bounce-absolute");

    if (connectionReady && isRecording) {
      startActualRecording();
    }

    return () => {
      // Safely disconnect audio nodes only if they are connected
      if (nodesConnectedRef.current && sourceNodeRef.current && processorRef.current) {
        try {
          sourceNodeRef.current.disconnect(processorRef.current);
          log("Source node disconnected successfully");
        } catch (err) {
          log(`Error disconnecting source node: ${err.message}`);
        }

        try {
          processorRef.current.disconnect();
          log("Processor node disconnected successfully");
        } catch (err) {
          log(`Error disconnecting processor node: ${err.message}`);
        }
        
        nodesConnectedRef.current = false;
      }

      if (audioContextRef.current && audioContextRef.current.state !== 'closed') {
        audioContextRef.current.close().catch(err => {
          log(`Error closing AudioContext: ${err.message}`);
        });
      }

      if (mediaRecorderRef.current?.state !== 'inactive') {
        mediaRecorderRef.current?.stop();
        mediaRecorderRef.current?.stream?.getTracks().forEach(track => track.stop());
      }
    };
  }, [connectionReady, isRecording]);

  const toggleRecording = () => {
    if (isRecording) {
      setIsRecording(false);
      stopRecording();
    } else {
      setIsRecording(true);
    }
  };

  const stopRecording = () => {
    // Safely disconnect audio nodes only if they are connected
    if (nodesConnectedRef.current && sourceNodeRef.current && processorRef.current) {
      try {
        sourceNodeRef.current.disconnect(processorRef.current);
        log("Source node disconnected successfully");
      } catch (err) {
        log(`Error disconnecting source node: ${err.message}`);
      }

      try {
        processorRef.current.disconnect();
        log("Processor node disconnected successfully");
      } catch (err) {
        log(`Error disconnecting processor node: ${err.message}`);
      }
      
      nodesConnectedRef.current = false;
    }

    if (mediaRecorderRef.current?.state !== 'inactive') {
      mediaRecorderRef.current?.stop();
      mediaRecorderRef.current?.stream?.getTracks().forEach(track => track.stop());
    }

    if (audioContextRef.current && audioContextRef.current.state !== 'closed') {
      audioContextRef.current.close().catch(err => {
        log(`Error closing AudioContext: ${err.message}`);
      });
    }

    log("Recording stopped");
  };

  const startActualRecording = () => {
    log("Starting actual recording process");
    const mediaStreamConstraints = { audio: true };

    navigator.mediaDevices.getUserMedia(mediaStreamConstraints)
      .then(stream => {
        log("Microphone access granted");

        audioContextRef.current = new AudioContext({ sampleRate: 16000 });
        sourceNodeRef.current = audioContextRef.current.createMediaStreamSource(stream);
        processorRef.current = audioContextRef.current.createScriptProcessor(4096, 1, 1);

        sourceNodeRef.current.connect(processorRef.current);
        processorRef.current.connect(audioContextRef.current.destination);
        nodesConnectedRef.current = true; // Set flag to indicate nodes are connected

        log("Audio processing pipeline set up");

        processorRef.current.onaudioprocess = (e) => {
          if (socketRef.current?.readyState === WebSocket.OPEN) {
            const inputData = e.inputBuffer.getChannelData(0);
            const pcm16 = float32ToInt16(inputData);
            const base64data = btoa(
              String.fromCharCode.apply(null, new Uint8Array(pcm16.buffer))
            );

            log(`Sending audio chunk: ${base64data.length} chars in base64`);
            socketRef.current.send(JSON.stringify({
              event_type: "audio_input_transmitting",
              event_data: base64data
            }));
          }
        };

        mediaRecorderRef.current = new MediaRecorder(stream);
        mediaRecorderRef.current.start();
        log("Recording started");
      })
      .catch(error => {
        log(`Error accessing microphone: ${error.message}`);
      });
  };

  const float32ToInt16 = (buffer) => {
    let l = buffer.length;
    const buf = new Int16Array(l);
    while (l--) {
      buf[l] = Math.min(1, buffer[l]) * 0x7FFF;
    }
    return buf;
  };

  
  const playNextAudio = () => {
    if (audioQueueRef.current.length === 0) {
      isPlayingRef.current = false;
      return;
    }
  
    const base64Data = audioQueueRef.current.shift();
    isPlayingRef.current = true;
  
    try {
      // Convert base64 to array buffer
      const binaryString = atob(base64Data);
      const bytes = new Uint8Array(binaryString.length);
      
      for (let i = 0; i < binaryString.length; i++) {
        bytes[i] = binaryString.charCodeAt(i);
      }
  
      // Check if we have valid data
      if (bytes.length < 2) {
        log("Received invalid audio data (too short). Skipping...");
        isPlayingRef.current = false;
        playNextAudio(); // Try the next chunk
        return;
      }
      
      // Create audio context with explicit sample rate matching the server
      const audioContext = new (window.AudioContext || window.webkitAudioContext)({
        sampleRate: 16000 // CRITICAL: Match the sample rate from the server
      });
      
      // Create a WAV header for the PCM data
      const wav = createWavFromPCM(bytes);
      
      // Use the built-in decoder
      audioContext.decodeAudioData(
        wav.buffer,
        (audioBuffer) => {
          // Create a source node
          const source = audioContext.createBufferSource();
          source.buffer = audioBuffer;
          
          // IMPORTANT: Set the playback rate to ensure correct speed
          source.playbackRate.value = 1.5;
          
          // Connect to destination and play
          source.connect(audioContext.destination);
          
          source.onended = () => {
            log("Audio playback finished");
            playNextAudio();
          };
          
          source.start(0);
          log("Audio playback started successfully");
        },
        (err) => {
          log(`Audio decoding failed: ${err}. Skipping this chunk.`);
          isPlayingRef.current = false;
          playNextAudio(); // Try the next chunk
        }
      );
    } catch (error) {
      log(`Error processing audio: ${error.message}`);
      isPlayingRef.current = false;
      playNextAudio(); // Try the next chunk
    }
  };

  const handleAudioResponse = (data) => {
    if (!data || data.length === 0) {
      log("Received empty audio data. Ignoring...");
      return;
    }
    
    // Add the new audio data to the queue
    audioQueueRef.current.push(data);
    log(`Audio added to queue. Queue length: ${audioQueueRef.current.length}`);
    
    // If not currently playing, start playing the queue
    if (!isPlayingRef.current) {
      playNextAudio();
    } else {
      log("Currently playing audio, new audio added to queue and will play when current audio finishes");
    }
  };
  // Improved WAV creation function with correct sample rate
  const createWavFromPCM = (pcmData) => {
    const numChannels = 1;
    const sampleRate = 16000; // MUST match the sample rate from the server
    const bitsPerSample = 16;
    
    // Calculate sizes
    const dataSize = pcmData.length;
    const wavSize = 44 + dataSize;
    
    // Create a buffer for the WAV file
    const wav = new Uint8Array(wavSize);
    
    // WAV header (44 bytes)
    const setString = (offset, string) => {
      for (let i = 0; i < string.length; i++) {
        wav[offset + i] = string.charCodeAt(i);
      }
    };
    
    const setUint32 = (offset, value) => {
      wav[offset] = value & 0xff;
      wav[offset + 1] = (value >> 8) & 0xff;
      wav[offset + 2] = (value >> 16) & 0xff;
      wav[offset + 3] = (value >> 24) & 0xff;
    };
    
    const setUint16 = (offset, value) => {
      wav[offset] = value & 0xff;
      wav[offset + 1] = (value >> 8) & 0xff;
    };
    
    // RIFF chunk descriptor
    setString(0, 'RIFF');
    setUint32(4, 36 + dataSize);
    setString(8, 'WAVE');
    
    // fmt sub-chunk
    setString(12, 'fmt ');
    setUint32(16, 16); // Subchunk1Size (16 for PCM)
    setUint16(20, 1); // AudioFormat (1 for PCM)
    setUint16(22, numChannels);
    setUint32(24, sampleRate); // CRITICAL: Correct sample rate
    setUint32(28, sampleRate * numChannels * bitsPerSample / 8); // ByteRate
    setUint16(32, numChannels * bitsPerSample / 8); // BlockAlign
    setUint16(34, bitsPerSample);
    
    // data sub-chunk
    setString(36, 'data');
    setUint32(40, dataSize);
    
    // Copy the PCM data
    wav.set(pcmData, 44);
    
    return wav;
  };
  
  return (
    <div>
      <div id="centered-text">
        <h1>Greenview Virtual Receptionist</h1>
      </div>
      <h2 id="instruction" className="absoluteUppies">Hello visitor! How can I help you?</h2>
      <div id="speak-button">
        <button
          id="speak"
          onClick={toggleRecording}
          disabled={!connectionReady}
          style={{
            padding: '8px 16px',
            background: '#0097A7',
            color: 'white',
            border: 'none',
            borderRadius: '5px',
            cursor: connectionReady ? 'pointer' : 'not-allowed',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            gap: '6px',
            flexDirection: 'row',
            whiteSpace: 'nowrap',
            minWidth: 'fit-content',
            opacity: connectionReady ? 1 : 0.7
          }}
        >
          <img
            src="/mic.svg"
            width={18}
            height={18}
            alt={isRecording ? "Stop Recording" : "Start Recording"}
            style={{ flexShrink: 0 }}
            id="mic"
          />
          <span id="mic-text">
            {!connectionReady ? 'Connecting...' : 
             isRecording ? 'Stop Recording' : 'Start Recording'}
          </span>
        </button>
      </div>
      <div id="data" ref={dataRef}></div>
      <div id="summary" ref={summaryRef}></div>
      <div style={{ 
        marginTop: '20px',
        border: '1px solid #ccc', 
        padding: '10px', 
        height: '200px', 
        overflowY: 'scroll'
      }}>
        <h3>Logs</h3>
        <ul style={{ listStyleType: 'none', padding: 0 }}>
          {logMessages.map((msg, index) => (
            <li key={index} style={{ marginBottom: '5px', fontSize: '0.9em' }}>{msg}</li>
          ))}
        </ul>
      </div>
    </div>
  );
}