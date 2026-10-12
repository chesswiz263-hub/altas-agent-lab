'use strict';
const form=document.getElementById('loginForm');
const error=document.getElementById('error');
form.addEventListener('submit',async event=>{
 event.preventDefault();
 const button=document.getElementById('submit');button.disabled=true;error.textContent='';
 try{
  const response=await fetch('/auth/login',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({password:document.getElementById('password').value})});
  if(!response.ok){const data=await response.json();throw Error(data.detail||'Could not sign in');}
  document.getElementById('password').value='';location.replace('/');
 }catch(err){error.textContent=err.message;button.disabled=false;}
});
