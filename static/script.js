async function generateAudio(){
const text=document.getElementById('text').value;
const voice=document.getElementById('voice').value;
const style=document.getElementById('style').value || 'Speak naturally';
const status=document.getElementById('status');
const player=document.getElementById('player');
const download=document.getElementById('download');
status.innerText='Generating...';
const res=await fetch('/generate',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({text,voice,style})});
const data=await res.json();
if(data.file){player.src=data.file;player.style.display='block';player.play();download.href=data.file;download.style.display='inline';status.innerText='Done';}else{status.innerText='Error';}
}
