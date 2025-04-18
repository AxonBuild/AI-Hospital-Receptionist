// page.js
"use client"; // This is important to enable client-side functionality

import { useEffect, useRef } from "react";
import Image from "next/image";
import styles from "./page.module.css";

export default function Home() {
  // Create refs to access DOM elements
  const startButtonRef = useRef(null);
  const stopButtonRef = useRef(null);
  const dataRef = useRef(null);
  const summaryRef = useRef(null);
  const audioRef = useRef(null);
  const canvasRef = useRef(null);
  const fileInputRef = useRef(null);

  useEffect(() => {
    let interval = 10;
    let mediaRecorder;
    let socket;

    const startRecording = () => {
      socket = new WebSocket('ws://localhost:8000/ws');
      socket.onopen = () => {
        // send the initial settings here, like language, doctor speciality etc.
        socket.send(JSON.stringify({
          language: 'en',
          interval: interval,
          summary: 1,
          speciality: 'cardiologist',
          patientContext: 'patient has diabetes and high blood pressure',
          patientID: '1234'
        }));

        const mediaStreamConstraints = {
          audio: true,
        };
        
        navigator.mediaDevices.getUserMedia(mediaStreamConstraints)
          .then(stream => {
            mediaRecorder = new MediaRecorder(stream, {
              mimeType: 'audio/webm',
              audioBitsPerSecond: 16000
            });
            mediaRecorder.start(interval * 1000);  // Start recording and send chunks every second
            
            mediaRecorder.ondataavailable = event => {
              let reader = new FileReader();
              reader.onloadend = () => {
                if (reader.readyState == FileReader.DONE) {
                  console.log(reader.result.byteLength);
                  socket.send(reader.result);
                }
              };
              reader.readAsArrayBuffer(event.data);
            };
          });
      };

      socket.onmessage = event => {
        let data = JSON.parse(event.data);
        if (data.hasOwnProperty("summary")) {
          if (summaryRef.current) {
            summaryRef.current.innerHTML = event.data;
          }
        } else {
          if (dataRef.current) {
            dataRef.current.innerHTML = event.data;
          }
        }
      };
    };

    const stopRecording = () => {
      if (mediaRecorder) {
        mediaRecorder.stop();
      }
      if (socket) {
        let encoder = new TextEncoder();
        let data = encoder.encode('stop');
        socket.send(data);
      }
    };

    // Add event listeners
    const startButton = startButtonRef.current;
    const stopButton = stopButtonRef.current;

    if (startButton) {
      startButton.addEventListener('click', startRecording);
    }

    if (stopButton) {
      stopButton.addEventListener('click', stopRecording);
    }

    // Clean up event listeners on component unmount
    return () => {
      if (startButton) {
        startButton.removeEventListener('click', startRecording);
      }
      if (stopButton) {
        stopButton.removeEventListener('click', stopRecording);
      }
      if (socket) {
        socket.close();
      }
    };
  }, []); // Empty dependency array means this effect runs once on mount

  return (
    <div>
      <div id="centered-text">
        <h1>Hospital Virtual Receptionist</h1>
      </div>
      <div id="speak-button">
        <button id="speak">
          <Image src="/mic.svg" width={24} height={24} alt="Microphone" />
        </button>
      </div>
      <div id="content">
        <input type="file" id="thefile" accept="audio/*" ref={fileInputRef} />
        <canvas id="canvas" ref={canvasRef}></canvas>
        <audio id="audio" ref={audioRef}></audio>
      </div>
      <button id="start" ref={startButtonRef}>Start</button>
      <button id="stop" ref={stopButtonRef}>Stop</button>
      <div id="data" ref={dataRef}></div>
      <div id="summary" ref={summaryRef}></div>
    </div>
  );
}