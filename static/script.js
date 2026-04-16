const btn=document.getElementById('btn'),player=document.getElementById('player');
btn.onclick=async()=>{const text=document.getElementById('text').value,voice=document.getElementById('voice').value;btn.disabled=true;btn.innerText='Generating...';const r=await fetch('/generate',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({text,voice})});const d=await r.json();if(d.status==='success'){player.src=d.audio_url;player.play();document.getElementById('download').href=d.audio_url;}else alert(d.message);btn.disabled=false;btn.innerText='Generate';}
document.getElementById('speed').oninput=e=>player.playbackRate=e.target.value;
document.getElementById('pitch').oninput=e=>player.preservesPitch=false;
