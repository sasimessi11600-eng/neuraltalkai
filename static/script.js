// Gemini 2.5 Flash Preview TTS-க்கான சரியான குரல் பட்டியல்கள்
const voicesByLanguage = {
    "ta-IN": [
        { name: "Puck (Gemini - Fast)", id: "puck" },
        { name: "Charon (Gemini - Deep)", id: "charon" },
        { name: "Kore (Gemini - Soft)", id: "kore" },
        { name: "Fenrir (Gemini - Bold)", id: "fenrir" }
    ],
    "en-IN": [
        { name: "Puck (Modern)", id: "puck" },
        { name: "Charon (Deep)", id: "charon" },
        { name: "Kore (Calm)", id: "kore" }
    ],
    "hi-IN": [
        { name: "Puck (Hindi Style)", id: "puck" },
        { name: "Charon (Hindi Style)", id: "charon" }
    ]
};

// பக்கத்தை லோடு செய்யும் போது குரல்களைக் காட்டுதல்
window.onload = () => {
    updateVoices();
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

// செக்பாக்ஸ் டிக் செய்தவுடன் பட்டனை எனேபிள் செய்தல்
function toggleButton() {
    const checkbox = document.getElementById('termsCheckbox');
    const btn = document.getElementById('generateBtn');
    btn.disabled = !checkbox.checked;
}

// ஆடியோ ஜெனரேட் செய்யும் முதன்மை பங்க்ஷன்
async function handleGenerate() {
    const textInput = document.getElementById('textInput');
    const voiceSelect = document.getElementById('voiceSelect');
    const btn = document.getElementById('generateBtn');
    const statusMsg = document.getElementById('statusMsg');
    const audioContainer = document.getElementById('audioPlayerContainer');
    const audioPlayer = document.getElementById('audioPlayer');

    if (!textInput.value.trim()) {
        alert("தயவுசெய்து ஏதாவது டைப் செய்யவும்!");
        return;
    }

    // பட்டனை லோடிங் நிலைக்கு மாற்றுதல்
    btn.disabled = true;
    btn.innerText = "Generating... ⏳";
    statusMsg.innerText = "தயவுசெய்து காத்திருக்கவும்...";

    try {
        const response = await fetch("/generate", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                text: textInput.value,
                voice: voiceSelect.value,
                user_id: "test_user" // நாம் Firebase-ல் உருவாக்கிய Document ID
            })
        });

        const result = await response.json();

        if (response.status === 200) {
            statusMsg.style.color = "#4ade80";
            statusMsg.innerText = "வெற்றிகரமாக உருவாக்கப்பட்டது!";
            
            // ஆடியோ பிளேயரைக் காட்டுதல்
            audioPlayer.src = result.audio_url;
            audioContainer.style.display = "block";
            audioPlayer.play();

            // வாலட் பேலன்ஸை அப்டேட் செய்தல்
            document.getElementById('balanceDisplay').innerText = `${result.remaining_credits.toLocaleString()} Credits`;
        } else {
            statusMsg.style.color = "#f87171";
            statusMsg.innerText = "Error: " + result.message;
        }
    } catch (error) {
        statusMsg.innerText = "சர்வர் இணைப்பில் கோளாறு!";
        console.error(error);
    } finally {
        btn.disabled = false;
        btn.innerText = "🚀 Generate Audio";
    }
}
