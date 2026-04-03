import os
import json
from flask import Flask, request, send_file, render_template_string
from google.cloud import texttospeech
from google.oauth2 import service_account

app = Flask(__name__)

def get_client():
    key_json = os.environ.get('GOOGLE_CLOUD_KEY') 
    if key_json:
        creds_info = json.loads(key_json)
        credentials = service_account.Credentials.from_service_account_info(creds_info)
        return texttospeech.TextToSpeechClient(credentials=credentials)
    else:
        # லோக்கலில் டெஸ்ட் பண்ணும்போது (உங்க லேப்டாப்ல)
        return texttospeech.TextToSpeechClient.from_service_account_json('json_key_new.json')

client = get_client()

VOICES = {
    "0": "ta-IN-Chirp3-HD-Sulafat", "1": "ta-IN-Chirp3-HD-Puck", "2": "ta-IN-Chirp3-HD-Leda",
    "3": "ta-IN-Chirp3-HD-Kore", "4": "ta-IN-Chirp3-HD-Iapetus", "5": "ta-IN-Chirp3-HD-Despina",
    "6": "ta-IN-Chirp3-HD-Charon", "7": "ta-IN-Chirp3-HD-Alnilam", "8": "ta-IN-Chirp3-HD-Algenib",
    "9": "ta-IN-Chirp3-HD-Algieba", "10": "ta-IN-Chirp3-HD-Achernar"
}

@app.route('/')
def home():
    return render_template_string('''
<!DOCTYPE html>
<html>
<head>
    <title>NeuralTalk AI - HD</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body{background:#0f0c29; color:white; font-family: sans-serif; text-align:center; padding:20px;}
        .container{max-width:500px; margin:auto; background:#16213e; padding:25px; border-radius:20px;}
        textarea, select, button{width:100%; padding:15px; margin:10px 0; border-radius:10px; border:none; font-size:16px;}
        button{background:#ff6b6b; color:white; font-weight:bold; cursor:pointer;}
        audio{width:100%; margin-top:20px;}
        #download{display:none; margin-top:15px; color:#4ecdc4; text-decoration:none;}
    </style>
</head>
<body>
    <div class="container">
        <h1>🎙️ NeuralTalk AI</h1>
        <select id="voiceIdx">
            <option value="0">Sulafat (HD)</option><option value="1">Puck (HD)</option>
            <option value="2">Leda (HD)</option><option value="3">Kore (HD)</option>
            <option value="4">Iapetus (HD)</option><option value="5">Despina (HD)</option>
            <option value="6">Charon (HD)</option><option value="7">Alnilam (HD)</option>
            <option value="8">Algenib (HD)</option><option value="9">Algieba (HD)</option>
            <option value="10">Achernar (HD)</option>
        </select>
        <textarea id="myText" rows="5" placeholder="Tamil story paste pannunga..."></textarea>
        <button onclick="generateAudio()" id="btn">Generate & Play</button>
        <audio id="player" controls></audio>
        <br><a id="download" href="#">⬇️ Download MP3</a>
    </div>
    <script>
        async function generateAudio() {
            const btn = document.getElementById('btn');
            const text = document.getElementById('myText').value;
            const vIdx = document.getElementById('voiceIdx').value;
            if(!text) { alert("Text enter pannunga"); return; }
            btn.innerText = "Processing..."; btn.disabled = true;
            const res = await fetch(`/speak?text=${encodeURIComponent(text)}&vIdx=${vIdx}`);
            const blob = await res.blob();
            const url = window.URL.createObjectURL(blob);
            const player = document.getElementById('player');
            const download = document.getElementById('download');
            player.src = url; player.play();
            download.href = url; download.download = "voice.mp3";
            download.style.display = "inline-block";
            btn.innerText = "Generate & Play"; btn.disabled = false;
        }
    </script>
</body>
</html>
''')

@app.route('/speak')
def speak():
    text = request.args.get('text', 'வணக்கம்')
    v_idx = request.args.get('vIdx', '0')
    voice_name = VOICES.get(v_idx, "ta-IN-Chirp3-HD-Sulafat")
    input_text = texttospeech.SynthesisInput(text=text)
    voice = texttospeech.VoiceSelectionParams(language_code="ta-IN", name=voice_name)
    audio_config = texttospeech.AudioConfig(audio_encoding=texttospeech.AudioEncoding.MP3)
    response = client.synthesize_speech(input=input_text, voice=voice, audio_config=audio_config)
    with open("output.mp3", "wb") as out:
        out.write(response.audio_content)
    return send_file("output.mp3", mimetype="audio/mpeg")

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))