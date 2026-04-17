async function loadData(){
 const l=await fetch('/languages').then(r=>r.json());
 const v=await fetch('/voices').then(r=>r.json());
 const lang=document.getElementById('language');
 const voice=document.getElementById('voice');
 Object.entries(l.languages).forEach(([k,n])=>lang.innerHTML+=`<option value="${k}">${n}</option>`);
 v.voices.forEach(x=>voice.innerHTML+=`<option value="${x}">${x}</option>`);
}
loadData();

const pitch=document.getElementById('pitch');
pitch.oninput=()=>document.getElementById('pitchValue').innerText=pitch.value;

document.getElementById('generateBtn').onclick=async()=>{
 const text=document.getElementById('text').value.trim();
 if(!text){alert('Enter text');return;}
 const body={
   text,
   language:document.getElementById('language').value,
   voice:document.getElementById('voice').value,
   pitch:document.getElementById('pitch').value
 };
 const btn=document.getElementById('generateBtn');
 btn.disabled=true; btn.innerText='Generating...';
 const res=await fetch('/generate',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
 const data=await res.json();
 btn.disabled=false; btn.innerText='Generate Audio';
 if(data.status==='success'){
   document.getElementById('result').style.display='block';
   const p=document.getElementById('player');
   p.src=data.audio_url; p.play();
   document.getElementById('downloadBtn').href=data.audio_url;
 }else{alert(data.message||'Error');}
};
