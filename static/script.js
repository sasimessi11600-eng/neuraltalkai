const pitch = document.getElementById("pitch");
const pitchValue = document.getElementById("pitchValue");

pitch.oninput = function () {
    pitchValue.innerText = this.value;
};

async function generateAudio() {
    const text = document.getElementById("text").value;
    const language = document.getElementById("language").value;
    const voice = document.getElementById("voice").value;
    const customStyle = document.getElementById("style").value;
    const pitchLevel = document.getElementById("pitch").value;

    const status = document.getElementById("status");
    const player = document.getElementById("player");
    const download = document.getElementById("download");

    if (!text.trim()) {
        status.innerText = "Please enter text";
        return;
    }

    const style =
        customStyle ||
        `Speak naturally in ${language} with pitch ${pitchLevel}`;

    status.innerText = "Generating...";
    player.style.display = "none";
    download.style.display = "none";

    try {
        const res = await fetch("/generate", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                text: text,
                voice: voice,
                style: style
            })
        });

        const data = await res.json();

        if (data.file) {
            player.src = data.file;
            player.style.display = "block";
            player.play();

            download.href = data.file;
            download.innerText = "Download Audio";
            download.style.display = "block";

            status.innerText = "Done";
        } else {
            status.innerText = "Failed";
        }

    } catch (error) {
        status.innerText = "Server Error";
    }
}
