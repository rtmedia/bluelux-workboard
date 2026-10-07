/* Conservative suggestions, not a claim about Git or project completion. */
'use strict';
const WorkboardFocus = (() => {
 const token=t=>String(t.requestAt||t.lastMessageAt||t.updatedAt||'');
 const result=(bucket,label,reason,next='Review the last response and decide what remains.')=>({bucket,label,reason,next});
 function evidence(t,delivery={}){
  const repos=(delivery.repositories||[]).filter(r=>t.projectIds.includes(r.repoId));
  const fresh=r=>r.defaultCommit&&r.checkedAt&&Date.now()-Date.parse(r.checkedAt)<10*60e3;
  const refs=[];
  for(const url of t.prs||[]){const repo=repos.find(r=>url.startsWith((r.remote||'NO_REMOTE')+'/pull/'));const pr=repo?.pullRequests?.[url];refs.push({kind:'pr',url,repoId:repo?.repoId,state:repo&&fresh(repo)?pr?.state||'unknown':'unknown',branch:pr?.branch,sha:pr?.sha});}
  for(const commit of t.commits||[]){const candidates=repos.filter(r=>(!commit.repo||r.remote==='https://github.com/'+commit.repo)&&r.commits?.[commit.sha]?.sha);const repo=candidates.length===1?candidates[0]:null;const proof=repo?.commits?.[commit.sha];refs.push({kind:'commit',sha:proof?.sha||commit.sha,repoId:repo?.repoId,state:repo&&fresh(repo)?proof.state:'unknown',url:repo&&proof?.sha?repo.remote+'/commit/'+proof.sha:null});}
  const included=refs.length>0&&refs.every(r=>r.state==='included');
  const units=repos.flatMap(r=>(r.units||[]).filter(u=>refs.some(ref=>ref.repoId===r.repoId&&((ref.branch&&ref.branch===u.branch)||(ref.sha&&ref.sha===u.sha)))).map(u=>({...u,repoId:r.repoId})));
  return {refs,included,units,cleanup:units.filter(u=>u.cleanup),branches:[...new Set(refs.map(ref=>repos.find(r=>r.repoId===ref.repoId)?.defaultBranch).filter(Boolean))]};
 }
 function classify(t,tasks=[],choice=null,proof={refs:[],included:false,cleanup:[]}){
  if(choice&&choice.requestToken===token(t)){
   const labels={focus:'Focus now',resume:'Keep open',completed:'Marked complete',parked:'Parked'};
   if(Object.hasOwn(labels,choice.status))return {...result(choice.status,labels[choice.status],'Your Workboard choice.',choice.note||'Open the discussion to continue.'),manual:true};
  }
  if(choice&&['completed','parked'].includes(choice.status))return result('review','New activity','New saved activity arrived after you closed or parked this discussion.','Review the new request and decide whether to resume.');
  if(proof.included&&!(t.requestAt&&(!t.responseAt||Date.parse(t.requestAt)>Date.parse(t.responseAt)))&&!(t.turnState==='interrupted'&&(!t.responseAt||!t.lastEventAt||Date.parse(t.lastEventAt)>Date.parse(t.responseAt))))return {...result('completed','On '+(proof.branches?.join(' / ')||'main'),'The explicitly cited work is included on the verified GitHub default branch.',proof.cleanup.length?'Review the leftover branches and worktrees in Cleanup.':'This work unit has reached its delivery milestone.'),verified:true};
  if(t.contextError)return result('review','History unavailable','The latest conversation could not be read.');
  if(t.requestIsRecent&&t.requestAt&&(!t.responseAt||Date.parse(t.requestAt)>Date.parse(t.responseAt)))return result('resume','Reply pending','The latest saved user request has no later final reply.','Open in Codex to check or continue the latest request.');
  if(t.turnState==='interrupted')return result('resume','Interrupted','The last saved turn was interrupted.','Check where the work stopped, then continue it.');
  if(proof.refs.some(r=>['open','outside'].includes(r.state)))return result('resume',proof.refs.some(r=>r.state==='open')?'Awaiting merge':'Delivery outstanding','Cited work has not been verified on GitHub main.','Continue the work or finish its review and merge.');
  if(!t.responseAt||!t.response)return result('review','Status unknown','No recent final response is available.');
  // Quoted examples/code are not evidence about this conversation's outcome.
  const text=t.response.replace(/```[\s\S]*?```/g,'').replace(/^\s*>.*$/gm,'').replace(/[*`]/g,'');
  const lines=text.split(/\n|(?<=[.!?])\s+/).map(s=>s.trim()).filter(Boolean);
  const pending=lines.find(s=>/^\s*[-*]?\s*\[ \]/.test(s))||lines.find(s=>/\b(?:still (?:need|needs|pending|blocked|remaining)|not yet (?:done|complete|completed|merged|pushed|deployed)|(?:remaining|next) (?:step|steps)\s*:|blocked (?:by|on)|waiting (?:on|for)|awaiting (?:approval|review)|could(?:n't| not) (?:finish|complete|verify)|needs? (?:your )?approval|(?:tests?|build|verification) (?:failed|fails|pending)|remaining\s*:)/i.test(s)&&!/^\s*(?:no |nothing |if |when )/i.test(s)&&!/\b(?:it|the (?:app|server|browser)) will still need\b/i.test(s));
  const finished=lines.slice(0,1).find(s=>/^(?:done|completed|finished|fixed|resolved|implemented|shipped|merged|deployed|all (?:done|set|requested .*complete))\b/i.test(s)&&!/[?]/.test(s)&&!/^\w+\s+(?:once|when|if)\b/i.test(s));
  const linked=tasks.filter(k=>t.projectIds.includes(k.projectId)&&/^[A-Z][A-Z0-9-]{3,}$/.test(k.key)&&new RegExp('(^|[^A-Za-z0-9-])'+k.key+'([^A-Za-z0-9-]|$)').test([t.request,t.response].join(' ')));
  const active=linked.filter(k=>['active','blocked'].includes(k.status));
  if(pending)return result('resume','Follow-up reported','The latest response reports unfinished work.',pending.slice(0,260));
  if(finished&&/\b(?:but|except|partial(?:ly)?|of \d+)\b/i.test(finished))return result('review','Check closeout','The opening completion statement has a qualification.');
  if(finished&&active.length)return result('review','Conflicting evidence','The reply reports completion, but '+active.map(k=>k.key).join(', ')+' is still active in the selected task file.','Check the result and reconcile the task file before closing.');
  if(finished)return result('review','Completion reported · unverified','The reply reports completion, but no cited PR or commit has yet been verified on GitHub main.','Check delivery evidence, or mark complete for work that is finished locally.');
  if(active.length){const k=active[0];return result('progress','Task follow-up','Latest discussion mentions '+active.map(k=>k.key).join(', ')+' in the selected task file.',k.checks?.find(c=>!c.done)?.text||'Review the active task and its remaining acceptance criteria.');}
  if(/\b(?:committed|pushed|merged|deployed)\b/i.test(text))return result('review','Check closeout','The reply mentions delivery activity, but that alone does not establish completion.','Check remaining tests, review, merge or release steps.');
  return result('review','Evidence unclear','Recent activity alone does not tell us whether work is finished.');
 }
 return {classify,token,evidence};
})();
if(typeof module!=='undefined')module.exports=WorkboardFocus;
