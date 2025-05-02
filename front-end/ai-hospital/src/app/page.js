"use client"; // This is important to enable client-side functionality

import { useEffect, useRef, useState } from "react";
import Image from "next/image";
import styles from "./page.module.css";

export default function Home() 
{
  // Add state to track recording status
  const [isRecording, setIsRecording] = useState(false);
  const [logMessages, setLogMessages] = useState([]);
  
  // Create refs to access DOM elements
  const dataRef = useRef(null);
  const summaryRef = useRef(null);
  const audioRef = useRef(null);
  const canvasRef = useRef(null);
  const fileInputRef = useRef(null);
  
  // Store mediaRecorder and socket in refs so they persist between renders
  const mediaRecorderRef = useRef(null);
  const socketRef = useRef(null);
  // Add refs for audio processing components
  const audioContextRef = useRef(null);
  const sourceNodeRef = useRef(null);
  const processorRef = useRef(null);

  // Custom logger function
  const log = (message) => {
    console.log(`[${new Date().toLocaleTimeString()}] ${message}`);
    setLogMessages(prev => [...prev, `[${new Date().toLocaleTimeString()}] ${message}`]);
  };

  // Define toggleRecording function as a React handler
  const toggleRecording = () => {
    log(`Toggle button clicked. Current isRecording state: ${isRecording}`);
    let mic = document.getElementById("mic")
    let micText = document.getElementById("mic-text")
    if (!isRecording) {
      // Initialize WebSocket if it doesn't exist or is closed
      if (!socketRef.current || socketRef.current.readyState !== WebSocket.OPEN) {
        socketRef.current = new WebSocket('ws://localhost:8000/ws');
        onMessage(); // Set up message handlers
        log("WebSocket initialized");
      }
      
      mic.classList.add("opacity-animation")
      micText.classList.add("opacity-animation")
      startRecording();
    } else {
      mic.classList.remove("opacity-animation")
      micText.classList.remove("opacity-animation")  
      stopRecording();
    }
  };

  const startRecording = () => {
    log("Starting recording process...");
    
    if (!socketRef.current || socketRef.current.readyState !== WebSocket.OPEN) {
      log("Establishing WebSocket connection");
      socketRef.current = new WebSocket('ws://localhost:8000/ws');
      onMessage();
    }
    
    const mediaStreamConstraints = {
      audio: true,
    };
    
    log("Requesting microphone access...");
    navigator.mediaDevices.getUserMedia(mediaStreamConstraints)
      .then(stream => {
        log("Microphone access granted");
        
        // Create an AudioContext to process the audio
        audioContextRef.current = new AudioContext({sampleRate: 16000});
        sourceNodeRef.current = audioContextRef.current.createMediaStreamSource(stream);
        processorRef.current = audioContextRef.current.createScriptProcessor(4096, 1, 1);
        
        sourceNodeRef.current.connect(processorRef.current);
        processorRef.current.connect(audioContextRef.current.destination);
        
        log("Audio processing pipeline set up");
        
        processorRef.current.onaudioprocess = (e) => {
          if (socketRef.current && socketRef.current.readyState === WebSocket.OPEN) {
            const inputData = e.inputBuffer.getChannelData(0);
            
            // Convert Float32Array to 16-bit PCM (similar to Python code)
            const pcm16 = float32ToInt16(inputData);
            
            // Base64 encode the 16-bit PCM data
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
        
        // Create a MediaRecorder to track state
        mediaRecorderRef.current = new MediaRecorder(stream);
        mediaRecorderRef.current.start();
        
        //Make sure state is updated properly
        setIsRecording(true);
        log("Recording state set to TRUE");
      })
      .catch(error => {
        log(`Error accessing microphone: ${error.message}`);
        console.error("Error accessing microphone:", error);
      });
  };

  // Helper function to convert Float32Array to Int16Array (equivalent to the Python function)
  const float32ToInt16 = (float32Array) => {
    const int16Array = new Int16Array(float32Array.length);
    
    for (let i = 0; i < float32Array.length; i++) {
      // Clip the value to [-1.0, 1.0] as in Python version
      const sample = Math.max(-1.0, Math.min(1.0, float32Array[i]));
      // Convert to 16-bit integer and store in the new array (multiplying by 32767 as in Python)
      int16Array[i] = Math.floor(sample * 32767);
    }
    
    return int16Array;
  };

  const onMessage = () => {
    socketRef.current.onmessage = event => {
      log(`Received WebSocket message: ${event.data.substring(0, 50)}...`);
      const mic = document.getElementById("mic")
      const micText = document.getElementById("mic-text")
      mic.classList.remove("opacity-animation")
      micText.classList.remove("opacity-animation")
      try {
        // Try to parse as JSON
        let data;
      try {
        data = JSON.parse(event.data);
      } catch (parseError) {
        log(`Failed to parse JSON: ${parseError.message}`);
        log(`Problematic JSON: ${event.data}`);
        return;
      }
      
      // Debug log the parsed data
      log(`Parsed data: ${JSON.stringify(data, null, 2)}`);
      
      // Verify the data structure
      if (!data || typeof data !== 'object') {
        log('Invalid data format - not an object');
        return;
      }
      
      if (!data.event_type) {
        log('Missing event_type in message');
        return;
      }
        // Handle different message types
        if (data.event_type == "audio_response_transmitting") {
          log("Received audio response, attempting to play...");
          
          // Convert base64 to array buffer
          const base64Data = data.event_data;
          const binaryString = atob(base64Data);
          const bytes = new Uint8Array(binaryString.length);
          
          for (let i = 0; i < binaryString.length; i++) {
            bytes[i] = binaryString.charCodeAt(i);
          }
          
          // Create audio context
          const audioContext = new (window.AudioContext || window.webkitAudioContext)({
            sampleRate: 16000 // Match your audio sample rate
          });
          
          // Create audio buffer from PCM data
          const audioBuffer = audioContext.createBuffer(1, bytes.length / 2, audioContext.sampleRate);
          const channelData = audioBuffer.getChannelData(0);
          
          // Convert 16-bit PCM to float32
          for (let i = 0; i < channelData.length; i++) {
            // Get 16-bit sample (2 bytes per sample)
            const sample = (bytes[i * 2] | (bytes[i * 2 + 1] << 8));
            // Convert to signed value
            const signedSample = sample >= 0x8000 ? sample - 0x10000 : sample;
            // Convert to float in range [-1, 1]
            channelData[i] = signedSample / 32768.0;
          }
          
          // Play audio
          const source = audioContext.createBufferSource();
          source.buffer = audioBuffer;
          source.connect(audioContext.destination);
          source.start(0);
          log("Audio playback started"); 
        } else {
          // For text/transcript messages
          if (dataRef.current) {
            dataRef.current.innerHTML = event.data;
          }
        }
      } catch (e) {
        // Not JSON or other error, just display as text
        if (dataRef.current) {
          dataRef.current.innerHTML = event.data;
        }
        mic.classList.remove("opacity-animation")
        micText.classList.remove("opacity-animation")
        log(`Error handling WebSocket message: ${e.message}`);
        console.error("Error handling WebSocket message:", e);
      }
    };
    
    socketRef.current.onerror = (error) => {
      const mic = document.getElementById("mic")
      const micText = document.getElementById("mic-text")
      mic.classList.remove("opacity-animation")
      micText.classList.remove("opacity-animation")
      log(`WebSocket error occurred`);
      console.log("WebSocket error:", error.message || "Unknown error"); ;
    };
    
    socketRef.current.onclose = (event) => {
      const mic = document.getElementById("mic")
      const micText = document.getElementById("mic-text")
      mic.classList.remove("opacity-animation")
      micText.classList.remove("opacity-animation")
      log(`WebSocket connection closed: ${event.code} ${event.reason}`);
    };
  };    

  const stopRecording = () => {
    // Stop recording without closing WebSocket
    log("Stopping recording but keeping WebSocket open...");
    log("Recording state before stopping: TRUE");
    
    // Disconnect the audio processing pipeline
    if (processorRef.current && sourceNodeRef.current) {
      sourceNodeRef.current.disconnect(processorRef.current);
      processorRef.current.disconnect();
      log("Audio processing pipeline disconnected");
    }
    
    // Close AudioContext if needed
    if (audioContextRef.current) {
      audioContextRef.current.close().then(() => {
        log("AudioContext closed");
      }).catch(err => {
        log(`Error closing AudioContext: ${err.message}`);
      });
      audioContextRef.current = null;
    }
    
    // Stop MediaRecorder and tracks
    if (mediaRecorderRef.current) {
      mediaRecorderRef.current.stop();
      log("MediaRecorder stopped");
      
      // Stop all tracks
      if (mediaRecorderRef.current.stream) {
        mediaRecorderRef.current.stream.getTracks().forEach(track => {
          track.stop();
          log(`Audio track stopped`);
        });
      }
      
      // Clear the MediaRecorder
      mediaRecorderRef.current = null;
    }
    
    // Notify the server we're stopping audio input (optional)
    if (socketRef.current && socketRef.current.readyState === WebSocket.OPEN) {
      try {
        log("Sending stop audio input notification");
        socketRef.current.send(JSON.stringify({
          event_type: "audio_input_stopped"
        }));
      } catch (e) {
        log(`Error sending stop notification: ${e.message}`);
      }
    }
    
    // Make sure state is updated
    setIsRecording(false);
    log("Recording state set to FALSE");
  };

  // Cleanup on component unmount
  useEffect(() => {
    let h2text = document.querySelector("#instruction")
    h2text.classList.add("bounce-absolute")
    
    return () => {
      log("Cleaning up resources on component unmount");
      
      // Disconnect audio processing if still connected
      if (processorRef.current && sourceNodeRef.current) {
        try {
          sourceNodeRef.current.disconnect(processorRef.current);
          processorRef.current.disconnect();
        } catch (e) {
          log(`Error disconnecting audio: ${e.message}`);
        }
      }
      
      // Close AudioContext
      if (audioContextRef.current) {
        audioContextRef.current.close().catch(err => {
          log(`Error closing AudioContext: ${err.message}`);
        });
      }
      
      // Close WebSocket
      if (socketRef.current) {
        socketRef.current.close();
        log("WebSocket connection closed on unmount");
      }
      
      // Stop MediaRecorder and tracks
      if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
        mediaRecorderRef.current.stop();
        
        if (mediaRecorderRef.current.stream) {
          mediaRecorderRef.current.stream.getTracks().forEach(track => {
            track.stop();
          });
        }
      }
    };
  }, []); 

  return (
    <div>
      <div id="centered-text">
        <h1>Greenview Virtual Receptionist</h1>
      </div>
      <h2 id = "instruction" className = "absoluteUppies">Hello visitor! How can I help you?</h2>
      <div id="speak-button">
        {/* Use onClick React handler instead of ref + addEventListener */}
        <button
          id="speak"
          onClick={toggleRecording}
          style={{
            padding: '8px 16px',
            background: '#0097A7',
            color: 'white',
            border: 'none',
            borderRadius: '5px',
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            gap: '6px',
            flexDirection: 'row',
            whiteSpace: 'nowrap',
            minWidth: 'fit-content'
          }}
        >
            <img
              src="/mic.svg"
              width={18}
              height={18}
              alt={isRecording ? "Stop Recording" : "Start Recording"}
              style={{ flexShrink: 0 }}
              id = "mic"
            />
            <span id = "mic-text">{isRecording ? 'Stop Recording' : 'Start Recording'}</span>
        </button>
      </div>
      <div id="data" ref={dataRef}></div>
      <div id="summary" ref={summaryRef}></div>
      
      {/* Logging display with auto-scroll to bottom */}
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