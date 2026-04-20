from flask import Flask, request, send_file
import whisper
import uuid
from gtts import gTTS
import os
from openai import OpenAI
import threading
import time

# ================= CONFIG =================
SERVER_IP = "192.168.1.5"   # 🔴 CHANGE THIS TO YOUR PC IP
PORT = 5000

# ================= INIT =================
app = Flask(__name__)

# API KEY CHECK
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    print("⚠️ WARNING: OPENAI_API_KEY not found! AI replies disabled.")

client = OpenAI(api_key=api_key) if api_key else None

print("🔄 Loading Whisper model...")
# ⚡ Use "tiny" for faster response
model = whisper.load_model("tiny")

# Create audio folder
AUDIO_FOLDER = "audio"
os.makedirs(AUDIO_FOLDER, exist_ok=True)

# ================= AUTO CLEANUP =================
def cleanup_files():
    while True:
        now = time.time()
        for file in os.listdir(AUDIO_FOLDER):
            path = os.path.join(AUDIO_FOLDER, file)
            if os.path.isfile(path):
                if now - os.path.getmtime(path) > 300:
                    try:
                        os.remove(path)
                    except:
                        pass
        time.sleep(60)

threading.Thread(target=cleanup_files, daemon=True).start()

# ================= COMMAND DETECTION =================
def detect_command(text):
    text = text.lower()

    if any(x in text for x in ["forward", "go forward", "ahead"]):
        return "FORWARD"

    if any(x in text for x in ["back", "backward", "reverse"]):
        return "BACKWARD"

    if any(x in text for x in ["left", "turn left"]):
        return "LEFT"

    if any(x in text for x in ["right", "turn right"]):
        return "RIGHT"

    if "stop" in text:
        return "STOP"

    return None

# ================= AI RESPONSE =================
def generate_ai_response(user_text):
    if not client:
        return "AI is not configured yet."

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a helpful robot. Speak short and clear."},
                {"role": "user", "content": user_text}
            ],
            max_tokens=120
        )
        return response.choices[0].message.content.strip()

    except Exception as e:
        print("OpenAI Error:", e)
        return "Sorry, I had trouble thinking."

# ================= MAIN ROUTE =================
@app.route('/voice', methods=['POST'])
def voice():
    try:
        file_id = str(uuid.uuid4())

        wav_path = os.path.join(AUDIO_FOLDER, f"{file_id}.wav")
        mp3_path = os.path.join(AUDIO_FOLDER, f"{file_id}.mp3")

        # Save incoming audio
        with open(wav_path, "wb") as f:
            f.write(request.data)

        print("\n🎤 Audio received")

        # ================= SPEECH TO TEXT =================
        result = model.transcribe(wav_path)
        text = result["text"].strip().lower()

        print("🧠 Heard:", text)

        if not text:
            return "STOP"

        # ================= COMMAND =================
        command = detect_command(text)
        if command:
            print("🚗 Command:", command)
            return command

        # ================= AI RESPONSE =================
        reply = generate_ai_response(text)
        print("🤖 Reply:", reply)

        # ================= TEXT TO SPEECH =================
        tts = gTTS(reply)
        tts.save(mp3_path)

        # ================= RETURN URL =================
        return f"http://{SERVER_IP}:{PORT}/audio/{file_id}.mp3"

    except Exception as e:
        print("❌ Server Error:", e)
        return "STOP"

# ================= AUDIO ROUTE =================
@app.route('/audio/<filename>')
def serve_audio(filename):
    path = os.path.join(AUDIO_FOLDER, filename)

    if os.path.exists(path):
        return send_file(path)

    return "File not found", 404

# ================= ROOT =================
@app.route('/')
def home():
    return "🤖 AI Robot Server Running"

# ================= RUN =================
if __name__ == "__main__":
    print(f"🚀 Server running at http://{SERVER_IP}:{PORT}")
    app.run(host="0.0.0.0", port=PORT, debug=False)
