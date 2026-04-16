document.getElementById('generate-btn').addEventListener('click', async () => {
    const text = document.getElementById('text').value;
    const voice = document.getElementById('voice').value;
    const btn = document.getElementById('generate-btn');

    if (!text) {
        alert("தயவுசெய்து ஏதேனும் டைப் செய்யுங்கள்!");
        return;
    }

    btn.disabled = true;
    btn.innerText = "Generating...";

    try {
        const response = await fetch('/generate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ text, voice })
        });

        const data = await response.json();
        if (data.status === "success") {
            const audio = document.getElementById('audio-player');
            audio.src = data.audio_url;
            document.getElementById('result').style.display = 'block';
            audio.play();
        } else {
            alert("Error: " + data.message);
        }
    } catch (error) {
        alert("சிக்னல் கோளாறு! மீண்டும் முயற்சிக்கவும்.");
    } finally {
        btn.disabled = false;
        btn.innerText = "Generate Audio";
    }
});
