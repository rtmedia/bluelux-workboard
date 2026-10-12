/* Conservative suggestions, not a claim about Git or project completion. */
'use strict';
const WorkboardFocus = (() => {
 const result=(bucket,label,reason,next='Review the last response and decide what remains.')=>({bucket,label,reason,next});
 function evidence(t,delivery={},workspaces=[]){
  const repos=(delivery.repositories||[]).filter(r=>t.projectIds.includes(r.repoId));
  const fresh=r=>r.defaultCommit&&r.checkedAt&&Date.now()-Date.parse(r.checkedAt)<10*60e3;
  const refs=[];
  for(const url of t.prs||[]){const repo=repos.find(r=>url.startsWith((r.remote||'NO_REMOTE')+'/pull/'));const pr=repo?.pullRequests?.[url];refs.push({kind:'pr',url,repoId:repo?.repoId,state:repo&&fresh(repo)?pr?.state||'unknown':'unknown',branch:pr?.branch,sha:pr?.sha});}
  for(const commit of t.commits||[]){const candidates=repos.filter(r=>(!commit.repo||r.remote==='https://github.com/'+commit.repo)&&r.commits?.[commit.sha]?.sha);const repo=candidates.length===1?candidates[0]:null;const proof=repo?.commits?.[commit.sha];refs.push({kind:'commit',sha:proof?.sha||commit.sha,repoId:repo?.repoId,state:repo&&fresh(repo)?proof.state:'unknown',url:repo&&proof?.sha?repo.remote+'/commit/'+proof.sha:null});}
  const included=refs.length>0&&refs.every(r=>r.state==='included');
  const units=repos.flatMap(r=>(r.units||[]).filter(u=>refs.some(ref=>ref.repoId===r.repoId&&((ref.branch&&ref.branch===u.branch)||(ref.sha&&ref.sha===u.sha)))).map(u=>({...u,repoId:r.repoId,evidenceFresh:fresh(r)}))).map(u=>({...u,decision:unitDecision(u,workspaces)}));
  return {refs,included,units,cleanup:units.filter(u=>u.decision.kind==='cleanup'),branches:[...new Set(refs.map(ref=>repos.find(r=>r.repoId===ref.repoId)?.defaultBranch).filter(Boolean))]};
 }
 function matchesTask(k,t){const body=(t.response||'').replace(/```[\s\S]*?```/g,'').replace(/^\s*>.*$/gm,'');return (t.projectIds||[]).includes(k.projectId)&&/^[A-Z][A-Z0-9-]+$/.test(k.key)&&/[0-9-]/.test(k.key)&&new RegExp('(^|[^A-Za-z0-9-])'+k.key+'([^A-Za-z0-9-]|$)').test([t.title,t.request,body].join(' '));}
 function classify(t,tasks=[],proof={refs:[],included:false,cleanup:[]}){
  if(t.contextError)return result('review','History unavailable','The latest conversation could not be read.');
  if(t.requestIsRecent&&t.requestAt&&(!t.responseAt||Date.parse(t.requestAt)>Date.parse(t.responseAt)))return result('resume','Reply pending','The latest saved user request has no later final reply.','Open in Codex to check or continue the latest request.');
  if(t.turnState==='interrupted')return result('resume','Interrupted','The last saved turn was interrupted.','Check where the work stopped, then continue it.');
  if(!t.responseAt||!t.response)return result('review','Status unknown','No recent final response is available.');
  // Quoted examples/code are not evidence about this conversation's outcome.
  const text=t.response.replace(/```[\s\S]*?```/g,'').replace(/^\s*>.*$/gm,'').replace(/[*`]/g,'');
  const lines=text.split(/\n|(?<=[.!?])\s+/).map(s=>s.trim()).filter(Boolean);
  const pendingLines=lines.filter(s=>/^\s*[-*]?\s*\[ \]/.test(s)||/\b(?:still (?:need|needs|pending|blocked|remaining)|not yet (?:done|complete|completed|merged|pushed|deployed)|(?:remaining|next) (?:step|steps)\s*:|blocked (?:by|on)|waiting (?:on|for)|awaiting (?:approval|review)|could(?:n't| not) (?:finish|complete|verify)|needs? (?:your )?approval|(?:tests?|build|verification) (?:failed|fails|pending)|remaining\s*:)/i.test(s)&&!/^\s*(?:no |nothing |if |when )/i.test(s)&&!/\b(?:it|the (?:app|server|browser)) will still need\b/i.test(s));
  const finished=lines.slice(0,1).find(s=>/^(?:done|completed|finished|fixed|resolved|implemented|shipped|merged|deployed|all (?:done|set|requested .*complete))\b/i.test(s)&&!/[?]/.test(s)&&!/^\w+\s+(?:once|when|if)\b/i.test(s));
  const linked=tasks.filter(k=>matchesTask(k,t));
  const active=linked.filter(k=>['active','blocked'].includes(k.status));
  const pending=pendingLines.find(s=>!(/\b(cleanup|clean up|delete|remove)\b.*\b(branch|worktree|checkout)\b/i.test(s)));
  const closed=linked.filter(k=>['done','deferred'].includes(k.status));
  const outside=proof.refs.some(r=>['open','outside'].includes(r.state));
  if(closed.length&&(pending||outside)){
   const newer=closed.some(k=>!k.source?.modified&&Number(k.source?.committedAt)*1000>Date.parse(t.responseAt));
   return {...result('review','Reconcile status',
    newer?'An older chat reports unfinished work, but a newer selected task file records related work as done or deferred.':'Chat or delivery evidence conflicts with the selected task record.',
    'Check '+closed.map(k=>k.key+' ('+k.status+')').join(', ')+(active.length?' alongside still-active '+active.map(k=>k.key).join(', '):'')+' before restarting work. Verify later completion and remaining scope in the original sources.'),
    action:'reconcile',conflict:true,records:linked,chatAt:t.responseAt,newerFile:newer};
  }
  if(outside)return result('delivery',proof.refs.some(r=>r.state==='open')?'Awaiting merge':'Verify delivery','Cited work has not been verified on GitHub main.','Check the exact work against current main before continuing or merging it.');
  if(pending)return result('resume','Follow-up reported','The latest response reports unfinished work.',pending.slice(0,260));
  if(finished&&/\b(?:but|except|partial(?:ly)?|of \d+)\b/i.test(finished))return result('review','Check closeout','The opening completion statement has a qualification.');
  if(proof.included&&!(t.requestAt&&(!t.responseAt||Date.parse(t.requestAt)>Date.parse(t.responseAt)))&&!(t.turnState==='interrupted'&&(!t.responseAt||!t.lastEventAt||Date.parse(t.lastEventAt)>Date.parse(t.responseAt))))return {...result('completed','On '+(proof.branches?.join(' / ')||'main'),'The explicitly cited work is included on the verified GitHub default branch.',proof.cleanup.length?'Review the leftover branches and worktrees in Cleanup.':'This work unit has reached its delivery milestone.'),verified:true};
  if(finished&&active.length)return {...result('review','Reconcile status','The reply reports completion, but '+active.map(k=>k.key).join(', ')+' is still active in the selected task file.','Check the result and reconcile the task file before closing.'),action:'reconcile',conflict:true,records:linked,chatAt:t.responseAt};
  if(finished)return result('review','Completion reported · unverified','The reply reports completion, but no cited PR or commit has yet been verified on GitHub main.','Reconcile delivery evidence and the source task record in Codex; local-only completion remains explicitly unverified.');
  if(closed.length&&!active.length)return {...result('review','Reconcile status','The selected task file records related work as done or deferred; this chat is not automatically unfinished.','Verify the task record and delivery before restarting or cleaning up.'),action:'reconcile',records:linked,chatAt:t.responseAt};
  if(active.length){const k=active[0];return result('progress','Task follow-up','Latest discussion mentions '+active.map(k=>k.key).join(', ')+' in the selected task file.',k.checks?.find(c=>!c.done)?.text||'Review the active task and its remaining acceptance criteria.');}
  if(/\b(?:committed|pushed|merged|deployed)\b/i.test(text))return result('review','Check closeout','The reply mentions delivery activity, but that alone does not establish completion.','Check remaining tests, review, merge or release steps.');
  return result('review','Evidence unclear','Recent activity alone does not tell us whether work is finished.');
 }
 // Recommendations are review routes, never deletion authorization.
 const primary=w=>w.primary===true||w.label==='Primary checkout';
 const fresh=r=>Boolean(r?.defaultCommit&&r?.checkedAt&&Date.now()-Date.parse(r.checkedAt)<10*60e3);
 function unitDecision(u,workspaces=[]){
  const linked=workspaces.filter(w=>(u.paths||[]).includes(w.path));
  const dirty=linked.some(w=>w.error||w.fileCount||w.conflicts);
  if(u.primaryRetained||linked.some(primary))return {kind:'keep',label:'Keep primary checkout',reason:dirty||u.pending?'Shared primary folder has unresolved work. Reconcile its changes in place; do not reset or remove it.':'Retain the primary folder. Review any temporary branch separately after checking active use.'};
  if(dirty||u.pending)return {kind:'preserve',label:'Preserve · reconcile work',reason:'Local changes or unique/unverified branch work remain. Establish what still needs delivery before cleanup.'};
  if(!u.evidenceFresh||linked.some(w=>w.head&&u.sha&&w.head!==u.sha))return {kind:'verify',label:'Verify current state',reason:'Delivery evidence is missing, expired or no longer matches this checkout tip. Keep it until checked.'};
  if(u.state==='included'&&u.cleanup)return {kind:'cleanup',label:'Review cleanup',reason:(u.blockers||[]).length?'Cited work is delivered, but files or other blockers still need inspection before any removal.':'Delivered temporary material is a cleanup candidate. Confirm ownership, files and active use before removal.'};
  return {kind:'verify',label:'Verify delivery · keep for now',reason:'Removal is not established. Check exact commits and current default-branch evidence before deciding.'};
 }
 function workspaceDecision(w,repositories=[]){
  if(primary(w))return {kind:'keep',label:'Keep primary checkout',action:w.error||w.fileCount||w.conflicts?'Reconcile local changes':'Review primary checkout',reason:w.error||w.fileCount||w.conflicts?'Shared project home with unresolved changes. Identify what belongs to which work unit; retain the folder.':'This is a primary project folder. Keep it even when a linked chat is finished.'};
  if(w.error||w.fileCount||w.conflicts)return {kind:'preserve',label:'Preserve · reconcile work',action:'Reconcile local changes',reason:'Changed, untracked or unreadable files need review. A linked chat is not proof of ownership.'};
  const repo=repositories.find(r=>r.repoId===w.repoId);
  const unit=(repo?.units||[]).find(u=>(u.paths||[]).includes(w.path)&&w.head&&u.sha===w.head);
  const decision=unit?unitDecision({...unit,evidenceFresh:fresh(repo)},[w]):{kind:'verify',label:'Verify delivery · keep for now',reason:'No current exact-tip delivery evidence for this checkout. No file changes does not mean safe to remove.'};
  return {...decision,action:decision.kind==='cleanup'?'Review cleanup in Codex':'Verify checkout in Codex'};
 }
 return {classify,evidence,unitDecision,workspaceDecision,matchesTask};
})();
if(typeof module!=='undefined')module.exports=WorkboardFocus;
