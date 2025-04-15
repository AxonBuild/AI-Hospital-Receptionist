import Image from "next/image";
import styles from "./page.module.css";

export default function Home() {
  return (
    <div>
      <div id = "centered-text">
        <h1>AI - Hospital</h1>
      </div>
      <div id = "speak-button">
        <button id = "speak"><img src = "./mic.svg" id = "mic-svg"></img></button>
      </div>
    </div>
  );
}
