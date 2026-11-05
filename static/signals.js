/* Pure, conservative observations. Provider events are data, never instructions. */
'use strict';
const WorkboardSignals=(()=>{
 const fresh=(stamp,now=Date.now(),age=10*60e3)=>Number.isFinite(Date.parse(stamp))&&now-Date.parse(stamp)>=-60000&&now-Date.parse(stamp)<age;
 const numeric=n=>typeof n==='number'&&Number.isFinite(n)&&n>=0;
 function session(t,now=Date.now()){
  const u=t.telemetry,at=t.lastActivityAt||t.lastEventAt;
  const current=fresh(at,now,5*60e3);
  const context=u&&numeric(u.lastTokens)&&numeric(u.contextWindow)&&u.contextWindow>0?Math.min(100,100*u.lastTokens/u.contextWindow):null;
  return {label:t.turnState==='started'?(current?'Recent activity':'Activity unconfirmed'):t.turnState==='finished'?'Turn ended':t.turnState==='interrupted'?'Interrupted':'Activity unknown',
   current:t.turnState==='started'&&current,at,context,stale:Boolean(u&&!fresh(u.observedAt,now)),handoff:context!==null&&context>=75};
 }
 function needsYou(t,now=Date.now()){
  if(!fresh(t.responseAt,now,30*864e5)||Date.parse(t.requestAt)>Date.parse(t.responseAt))return null;
  const lines=(t.response||'').replace(/```[\s\S]*?```/g,'').split(/\n|(?<=[.!?])\s+/);
  return lines.find(s=>!/^\s*(?:>|if\b|when\b|no\b|nothing\b)/i.test(s)&&!/\b(?:does not|doesn't|do not|don't|no longer)\b/i.test(s)&&!/\b(?:not|no longer|already)\s+(?:required|needed|waiting)\b/i.test(s)&&/\b(?:needs? your (?:account['’]s )?(?:approval|decision|input|code|passkey)|(?:awaiting|waiting for) your (?:approval|decision|input)|(?:please|you need to) (?:approve|choose|confirm)|requires? your (?:approval|code|passkey))\b/i.test(s))?.trim().slice(0,260)||null;
 }
 function collisions(threads,workspaces,now=Date.now()){
  return workspaces.map(w=>({workspace:w,threads:threads.filter(t=>!t.archived&&session(t,now).current&&(t.workspacePaths||[]).includes(w.path))})).filter(x=>x.threads.length>1);
 }
 function quota(t,now=Date.now()){
  const u=t.telemetry;
  return (u?.windows||[]).map(w=>({...w,remaining:numeric(w.usedPercent)&&w.usedPercent<=100?100-w.usedPercent:null,
   stale:!fresh(u.observedAt,now)||!numeric(w.resetsAt)||w.resetsAt*1000<=now}));
 }
 function changes(previous,next){
  if(!previous)return [];
  const result=[],oldThreads=new Map((previous.threads||[]).map(t=>[t.id,t])),oldWorkspaces=new Map((previous.workspaces||[]).map(w=>[w.path,w]));
  for(const t of next.threads||[]){const old=oldThreads.get(t.id);if(!old)continue;
   if(t.responseAt&&t.responseAt!==old.responseAt)result.push({kind:'chat',id:t.id,projectIds:t.projectIds,label:t.title+': new saved reply'});
  }
  for(const w of next.workspaces||[]){const old=oldWorkspaces.get(w.path);if(old&&JSON.stringify(w.files)!==JSON.stringify(old.files))result.push({kind:'workspace',id:w.path,projectIds:[w.repoId],label:w.label+': local file state changed'});}
  return result;
 }
 return {fresh,session,needsYou,collisions,quota,changes};
})();
if(typeof module!=='undefined')module.exports=WorkboardSignals;
