// page.js
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

  // Custom logger function
  const log = (message) => {
    console.log(`[${new Date().toLocaleTimeString()}] ${message}`);
    setLogMessages(prev => [...prev, `[${new Date().toLocaleTimeString()}] ${message}`]);
  };

  // Define toggleRecording function as a React handler
  const toggleRecording = () => {
    log(`Toggle button clicked. Current isRecording state: ${isRecording}`);
    
    if (!isRecording) {
      onMessage();
    } else {
      stopRecording();
    }
  };

  // const startRecording = () => {
  //   log("Starting recording process...");
    
  //   // Start recording
  //   socketRef.current = new WebSocket('ws://localhost:8000/ws');
    
  //   socketRef.current.onopen = () => {
  //     log("WebSocket connection established");
      
  //     const mediaStreamConstraints = {
  //       audio: true,
  //     };
      
  //     log("Requesting microphone access...");
  //     navigator.mediaDevices.getUserMedia(mediaStreamConstraints)
  //       .then(stream => {
  //         log("Microphone access granted");
          
  //         // Check if the browser supports the WebM format
  //         const mimeType = MediaRecorder.isTypeSupported('audio/webm') 
  //           ? 'audio/webm' 
  //           : 'audio/mp4';
          
  //         log(`Using MIME type: ${mimeType}`);
          
  //         mediaRecorderRef.current = new MediaRecorder(stream, {
  //           mimeType: mimeType,
  //           audioBitsPerSecond: 16000
  //         });
          
  //         const interval = 1; // Send audio chunks every 1 second
  //         mediaRecorderRef.current.start(interval * 1000);
  //         log(`Started recording, sending chunks every ${interval} second(s)`);
          
  //         mediaRecorderRef.current.ondataavailable = event => {
  //           if (event.data.size > 0) {
  //             log(`Audio chunk received: ${event.data.size} bytes`);
              
  //             // For this basic demo, convert the blob to base64 for easier transmission
  //             const reader = new FileReader();
  //             reader.onloadend = () => {
  //               if (reader.readyState === FileReader.DONE && socketRef.current && socketRef.current.readyState === WebSocket.OPEN) {
  //                 // Send as text since our backend is expecting text
  //                 const base64data = btoa(
  //                   new Uint8Array(reader.result)
  //                     .reduce((data, byte) => data + String.fromCharCode(byte), '')
  //                 );
                  
  //                 log(`Sending audio chunk: ${base64data.length} chars in base64`);
  //                 socketRef.current.send(JSON.stringify({
  //                   type: "audio_data",
  //                   format: mimeType,
  //                   data: base64data
  //                 }));
  //               }
  //             };
  //             reader.readAsArrayBuffer(event.data);
  //           }
  //         };
          
  //         //Make sure state is updated properly
  //         setIsRecording(true);
  //         log("Recording state set to TRUE");
  //       })
  //       .catch(error => {
  //         log(`Error accessing microphone: ${error.message}`);
  //         console.error("Error accessing microphone:", error);
  //       });
  //   };

    const onMessage = () => {
      socketRef.current.onmessage = event => {
      log(`Received WebSocket message: ${event.data.substring(0, 50)}...`);
      
      try {
        if (dataRef.current) {
          dataRef.current.innerHTML = event.data;
        }
      } catch (e) {
        log(`Error handling WebSocket message: ${e.message}`);
        console.error("Error handling WebSocket message:", e);
      }
    };
    
    socketRef.current.onerror = (error) => {
      log(`WebSocket error occurred`);
      console.error("WebSocket error:", error);
    };
    
    socketRef.current.onclose = (event) => {
      log(`WebSocket connection closed: ${event.code} ${event.reason}`);
    };
  };

  const stopRecording = () => {
    // Stop recording
    log("Stopping recording...");
    log("Recording state before stopping: TRUE");
    
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
    }
    
    if (socketRef.current && socketRef.current.readyState === WebSocket.OPEN) {
      try {
        log("Sending stop signal");
        socketRef.current.send(JSON.stringify({
          type: "command",
          command: "stop"
        }));
        
        // Close the socket after sending the stop command
        log("Closing WebSocket connection");
        socketRef.current.close();
        log("WebSocket connection closed by client");
      } catch (e) {
        log(`Error during recording stop: ${e.message}`);
        console.error("Error during recording stop:", e);
      }
    }
    
    // Make sure state is updated
    setIsRecording(false);
    log("Recording state set to FALSE");
  };

  // Cleanup on component unmount
  useEffect(() => {
    return () => {
      log("Cleaning up resources on true component unmount");
      
      if (socketRef.current) {
        socketRef.current.close();
      }
      
      if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
        mediaRecorderRef.current.stop();
        
        if (mediaRecorderRef.current.stream) {
          mediaRecorderRef.current.stream.getTracks().forEach(track => {
            track.stop();
          });
        }
      }
    };
  }, []); // Empty dependency array means this only runs on mount/unmount

  return (
    <div>
      <div id="centered-text">
        <h1>Hospital Virtual Receptionist</h1>
      </div>
      <div id="speak-button">
        {/* Use onClick React handler instead of ref + addEventListener */}
        <button 
          id="speak" 
          onClick={toggleRecording}
          style={{ 
            padding: '10px 20px',
            background: isRecording ? '#ff4d4d' : '#4caf50',
            color: 'white',
            border: 'none',
            borderRadius: '5px',
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            gap: '8px'
          }}
        >
          <img 
            src="/mic.svg" 
            width={24} 
            height={24} 
            alt={isRecording ? "Stop Recording" : "Start Recording"} 
          />
          {isRecording ? 'Stop Recording' : 'Start Recording'}
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