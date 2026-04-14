/* NeuralTalk AI Studio - Script */

async function generateAudio() {
    // 1. பயனரின் உள்ளீடுகளைப் பெறுதல்
    const email = document.getElementById('email').value;
    const text = document.getElementById('text').value;
    const lang = document.getElementById('language').value;
    const voice = document.getElementById('voice').value;
    const btn = document.getElementById('genBtn');
    const resultDiv = document.getElementById('result');
    const player = document.getElementById('audioPlayer');
    const creditsSpan = document.getElementById('credits');

    // 2. உள்ளீடுகள் சரியாக உள்ளதா எனச் சரிபார்த்தல்
    if (!email || !text) {
        alert("தயவுசெய்து Email மற்றும் Text இரண்டையும் உள்ளிடவும்!");
        return;
    }

    // 3. பட்டனை "Loading..." நிலைக்கு மாற்றுதல்
    btn.innerText = "உருவாக்கப்படுகிறது... (பொறுத்திருக்கவும்)";
    btn.disabled = true;
    resultDiv.style.display = 'none'; // பழைய முடிவுகளை மறைக்க

    // 4. Render Backend API-க்கு கோரிக்கை அனுப்புதல்
    try {
        // குறிப்பு: நீங்கள் Vercel-ல் ஹோஸ்ட் செய்தால், '/' என்பதற்குப் பதில் உங்கள் Render URL-ஐக் கொடுக்க வேண்டும்.
        // உதாரணமாக: 'https://neuraltalk-api.onrender.com/generate'
        const response = await fetch('/generate', { 
            method: 'POST',
            headers: { 
                'Content-Type': 'application/json',
                // தேவைப்பட்டால் CORS ஹெடர்களை இங்கே சேர்க்கலாம்
            },
            body: JSON.stringify({ email, text, language: lang, voice }) 
        });

        // 5. சர்வர் பதிலைச் சரிபார்த்தல்
        if (!response.ok) {
            // எரர் மெசேஜைப் பெறுதல்
            const errorData = await response.json();
            throw new Error(errorData.detail || "ஆடியோ உருவாக்குவதில் பிழை ஏற்பட்டது!");
        }

        // 6. வெற்றிகரமான பதிலை கையாளுதல்
        const data = await response.json();

        if (data.status === "success") {
            // முடிவுகளைக் காண்பித்தல்
            resultDiv.style.display = 'block';
            
            // Cache பிரச்சனையைத் தவிர்க்க Time Stamp சேர்க்கிறோம்
            const audioUrlWithCacheBuster = data.audio_url + "?t=" + new Date().getTime();
            player.src = audioUrlWithCacheBuster;
            
            // கிரெடிட்களை அப்டேட் செய்தல்
            creditsSpan.innerText = data.remaining_credits.toLocaleString(); 
            
            // ஆடியோவை பிளே செய்தல்
            player.play();
        } else {
            // எரர் மெசேஜ் காண்பித்தல்
            alert("பிழை: " + data.message);
        }
    } catch (error) {
        // இணைப்பில் பிழை ஏற்பட்டால்
        console.error("API Error:", error);
        alert("பிழை: " + error.message);
    } finally {
        // 7. பட்டனை பழைய நிலைக்கு மாற்றுதல்
        btn.innerText = "ஆடியோ உருவாக்கு";
        btn.disabled = false;
    }
}
