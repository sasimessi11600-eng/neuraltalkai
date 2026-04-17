// 1. 10 மொழிகள் மற்றும் அதற்கான 26+ குரல் மாடல்களின் பட்டியல்
const voicesByLanguage = {
    "ta-IN": [
        { name: "Arjun (Male)", id: "ta-IN-Wavenet-A" },
        { name: "Bhuvan (Male)", id: "ta-IN-Wavenet-B" },
        { name: "Chitra (Female)", id: "ta-IN-Wavenet-C" },
        { name: "Divya (Female)", id: "ta-IN-Wavenet-D" }
    ],
    "en-IN": [
        { name: "Puck (Gemini 2.5)", id: "Puck" },
        { name: "Charon (Deep)", id: "Charon" },
        { name: "Kore (Soft)", id: "Kore" },
        { name: "Fenrir (Bold)", id: "Fenrir" },
        { name: "Rohan (Male)", id: "en-IN-Wavenet-B" },
        { name: "Kavya (Female)", id: "en-IN-Wavenet-D" }
    ],
    "hi-IN": [
        { name: "Amit (Male)", id: "hi-IN-Wavenet-B" },
        { name: "Sagar (Male)", id: "hi-IN-Wavenet-C" },
        { name: "Ananya (Female)", id: "hi-IN-Wavenet-A" },
        { name: "Pooja (Female)", id: "hi-IN-Wavenet-D" }
    ],
    "te-IN": [
        { name: "Sagar (Male)", id: "te-IN-Standard-B" },
        { name: "Vani (Female)", id: "te-IN-Standard-A" }
    ],
    "kn-IN": [
        { name: "Rahul (Male)", id: "kn-IN-Wavenet-A" },
        { name: "Deepa (Female)", id: "kn-IN-Wavenet-B" }
    ],
    "ml-IN": [
        { name: "Manu (Male)", id: "ml-IN-Standard-B" },
        { name: "Aswathy (Female)", id: "ml-IN-Standard-A" }
    ],
    "bn-IN": [
        { name: "Basu (Male)", id: "bn-IN-Wavenet-B" },
        { name: "Ishani (Female)", id: "bn-IN-Wavenet-A" }
    ],
    "gu-IN": [
        { name: "Himesh (Male)", id: "gu-IN-Standard-B" },
        { name: "Dhara (Female)", id: "gu-IN-Standard-A" }
    ],
    "mr-IN": [
        { name: "Vinay (Male)", id: "mr-IN-Wavenet-B" },
        { name: "Lata (Female)", id: "mr-IN-Wavenet-A" }
    ],
    "pa-IN": [
        { name: "Gurpreet (Male)", id: "pa-IN-Wavenet-B" },
        { name: "Simran (Female)", id: "pa-IN-Wavenet-A" }
    ]
};

// 2. மொழியை மாற்றும்போது வாய்ஸ் செலக்ட் பாக்ஸை அப்டேட் செய்யும் பங்க்ஷன்
function updateVoices() {
    const langSelect = document.getElementById('langSelect');
    const voiceSelect = document.getElementById('voiceSelect');
    const selectedLang = langSelect.value;
    
    // பழைய குரல்களை நீக்கவும்
    voiceSelect.innerHTML = "";
    
    // புதிய மொழிக்கான குரல்களைச் சேர்க்கவும்
    if (voicesByLanguage[selectedLang]) {
        voicesByLanguage[selectedLang].forEach(voice => {
            const option = document.createElement('option');
            option.value = voice.id;
            option.textContent = voice.name;
            voiceSelect.appendChild(option);
        });
    }
}

// 3. ஆடியோவை உருவாக்கும் முக்கிய பங்க்ஷன்
async function handleGenerate() {
    const text = document.getElementById('storyInput').value;
    const voice = document.getElementById('voiceSelect').value;
    const terms = document.getElementById('terms_agree').checked;
    const btn = document.getElementById('generateBtn');

    if (!terms) {
        alert("விதிமுறைகளை ஏற்றுக்கொள்வதை உறுதிப்படுத்தவும்!");
        return;
    }

    if (!text.trim()) {
        alert("தயவுசெய்து ஏதாவது எழுதவும்!");
        return;
    }

    btn.innerText = "⏳ Processing...";
    btn.disabled = true;

    try {
        const response = await fetch('/generate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ text: text, voice: voice })
        });

        const result = await response.json();

        if (result.status === 'success') {
            const player = document.getElementById('audioPlayer');
            const downloadBtn = document.getElementById('downloadBtn');
            const playerContainer = document.getElementById('playerContainer');

            player.src = result.audio_url;
            playerContainer.classList.remove('hidden');
            downloadBtn.classList.remove('hidden');
            
            // டவுன்லோட் லிங்க் செட் செய்தல்
            downloadBtn.onclick = () => {
                const a = document.createElement('a');
                a.href = result.audio_url;
                a.download = "NeuralTalk-AI-Audio.wav";
                a.click();
            };

            alert("Audio Generated!");
        } else {
            alert("Error: " + result.message);
        }
    } catch (err) {
        alert("Server Error! இணையத்தை சரிபார்க்கவும்.");
    } finally {
        btn.innerText = "🚀 Generate Audio";
        btn.disabled = false;
    }
}

// பக்கம் லோட் ஆனவுடன் முதல் முறை ரன் செய்யவும்
window.onload = updateVoices;
