let uid = localStorage.getItem("uid") || "";

const pitch = document.getElementById("pitch");
const pitchValue = document.getElementById("pitchValue");

if (pitch) {
  pitch.oninput = function () {
    pitchValue.innerText = this.value;
  };
}

window.onload = async function () {
  if (uid) {
    await loadUser();
  }
};

async function signup() {
  const email = document.getElementById("email").value;
  const password = document.getElementById("password").value;
  const status = document.getElementById("status");

  const res = await fetch("/signup", {
    method: "POST",
    headers: {"Content-Type":"application/json"},
    body: JSON.stringify({ email, password })
  });

  const data = await res.json();

  if (data.uid) {
    status.innerText = "Signup success. Please Sign In.";
  } else {
    status.innerText = data.detail || "Signup failed";
  }
}

async function login() {
  const email = document.getElementById("email").value;
  const password = document.getElementById("password").value;
  const status = document.getElementById("status");

  const res = await fetch("/login", {
    method: "POST",
    headers: {"Content-Type":"application/json"},
    body: JSON.stringify({ email, password })
  });

  const data = await res.json();

  if (data.uid) {
    uid = data.uid;
    localStorage.setItem("uid", uid);
    await loadUser();
    status.innerText = "Login success";
  } else {
    status.innerText = "Login failed";
  }
}

async function loadUser() {
  const res = await fetch(`/me/${uid}`);
  const user = await res.json();

  document.getElementById("authBox").style.display = "none";
  document.getElementById("appBox").style.display = "block";
  document.getElementById("userEmail").innerText = user.email;
  document.getElementById("credits").innerText = user.credits;
}

async function buyPlan(amount) {
  const res = await fetch("/buy", {
    method: "POST",
    headers: {"Content-Type":"application/json"},
    body: JSON.stringify({ uid, amount })
  });

  const data = await res.json();

  if (data.success) {
    await loadUser();
    document.getElementById("status").innerText = "Plan activated";
  }
}

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

  const res = await fetch("/generate", {
    method: "POST",
    headers: {"Content-Type":"application/json"},
    body: JSON.stringify({
      uid,
      text,
      voice,
      style
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
    await loadUser();
  } else {
    status.innerText = data.detail || "Failed";
  }
}
