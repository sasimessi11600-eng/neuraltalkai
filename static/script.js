// Gemini 2.5 Flash Preview TTS-க்கான சரியான குரல் பட்டியல்கள்
const voicesByLanguage = {
    "ta-IN": [
        { name: "Puck (Gemini - Fast)", id: "puck" },
        { name: "Charon (Gemini - Deep)", id: "charon" },
        { name: "Kore (Gemini - Soft)", id: "kore" },
        { name: "Fenrir (Gemini - Bold)", id: "fenrir" },
        { name: "Aoede (Gemini - Clear)", id: "aoede" }
    ],
    "en-IN": [
        { name: "Puck (Modern)", id: "puck" },
        { name: "Charon (Deep Voice)", id: "charon" },
        { name: "Kore (Calm)", id: "kore" },
        { name: "Fenrir (Strong)", id: "fenrir" }
    ],
    "hi-IN": [
        { name: "Puck (Hindi Style)", id: "puck" },
        { name: "Charon (Hindi Style)", id: "charon" },
        { name: "Kore (Hindi Style)", id: "kore" }
    ]
    // மற்ற மொழிகளுக்கும் இதே பெயர்களை (puck, charon, etc.) பயன்படுத்தலாம்.
    // Gemini 2.5 மாடல் தானாகவே மொழியைப் புரிந்து கொண்டு பேசும்.
};

function updateVoices() {
    const langSelect = document.getElementById('langSelect');
    const voiceSelect = document.getElementById('voiceSelect');
    const selectedLang = langSelect.value;
    
    voiceSelect.innerHTML = "";
    
    if (voicesByLanguage[selectedLang]) {
        voicesByLanguage[selectedLang].forEach(voice => {
            const option = document.createElement('option');
            option.value = voice.id;
            option.textContent = voice.name;
            voiceSelect.appendChild(option);
        });
    }
}
// மற்ற handleGenerate பங்க்ஷன்கள் அப்படியே இருக்கட்டும்.
