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
  const nodesConnectedRef = useRef(false); // New ref to track connection state

  const log = (message) => {
    console.log(`[${new Date().toLocaleTimeString()}] ${message}`);
    setLogMessages(prev => [...prev, `[${new Date().toLocaleTimeString()}] ${message}`]);
  };

  useEffect(() => {
    if (!socketRef.current || socketRef.current.readyState !== WebSocket.OPEN) {
      socketRef.current = new WebSocket('ws://localhost:8000/ws');

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

  const handleAudioResponse = (data) => {
       // Convert base64 to array buffer
       const base64Data = data;
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