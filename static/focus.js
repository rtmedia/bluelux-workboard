/* Conservative suggestions, not a claim about Git or project completion. */
'use strict';
const WorkboardFocus = (() => {
 const token=t=>String(t.requestAt||t.lastMessageAt||t.updatedAt||'');
 const result=(bucket,label,reason,next='Review the last response and decide what remains.')=>({bucket,label,reason,next});
 function classify(t,tasks=[],choice=null){
  if(choice&&choice.requestToken===token(t)){
   const labels={focus:'Focus now',resume:'Keep open',completed:'Marked complete',parked:'Parked'};
   if(Object.hasOwn(labels,choice.status))return {...result(choice.status,labels[choice.status],'Your Workboard choice.',choice.note||'Open the discussion to continue.'),manual:true};
  }
  if(choice&&['completed','parked'].includes(choice.status))return result('review','New activity','New saved activity arrived after you closed or parked this discussion.','Review the new request and decide whether to resume.');
  if(t.contextError)return result('review','History unavailable','The latest conversation could not be read.');
  if(t.requestIsRecent&&t.requestAt&&(!t.responseAt||Date.parse(t.requestAt)>Date.parse(t.responseAt)))return result('resume','Reply pending','The latest saved user request has no later final reply.','Open in Codex to check or continue the latest request.');
  if(t.turnState==='interrupted')return result('resume','Interrupted','The last saved turn was interrupted.','Check where the work stopped, then continue it.');
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
  if(finished)return result('completed','Completion reported','The latest response reports completion; GitHub/release status is not independently verified.','Review the reported result if you need confirmation.');
  if(active.length){const k=active[0];return result('resume','Task recorded active','Latest discussion mentions '+active.map(k=>k.key).join(', ')+' in the selected task file.',k.checks?.find(c=>!c.done)?.text||'Review the active task and its remaining acceptance criteria.');}
  if(/\b(?:committed|pushed|merged|deployed)\b/i.test(text))return result('review','Check closeout','The reply mentions delivery activity, but that alone does not establish completion.','Check remaining tests, review, merge or release steps.');
  return result('review','Needs a decision','Recent activity alone does not tell us whether work is finished.');
 }
 return {classify,token};
})();
if(typeof module!=='undefined')module.exports=WorkboardFocus;
