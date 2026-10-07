const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const elements=new Map();
function element(){return {listeners:{},closest(){return null},getBoundingClientRect(){return {left:500,right:1000,top:0,bottom:800}},innerHTML:'',textContent:'',dataset:{},classList:{toggle(){}},setAttribute(){},addEventListener(type,fn){(this.listeners[type]??=[]).push(fn)},append(){},focus(){},select(){},showModal(){this.open=true},close(){this.open=false}};}
const document={querySelector:s=>{if(!elements.has(s))elements.set(s,element());return elements.get(s)},querySelectorAll:()=>[],createElement:element,body:element(),addEventListener(){}};
const context=vm.createContext({document,window:{addEventListener(){}},fetch:()=>new Promise(()=>{}),setInterval(){},setTimeout(){},clearTimeout(){},URLSearchParams,console});
vm.runInContext(fs.readFileSync('static/focus.js','utf8'),context);
vm.runInContext(fs.readFileSync('static/cleanup.js','utf8'),context);
vm.runInContext(fs.readFileSync('static/app.js','utf8'),context);
vm.runInContext(`
state.data={checkedAt:new Date().toISOString(),projects:[{id:'r',name:'Example <Project>',core:true}],repositories:[{id:'r',stashes:[]}],documents:[],workspaces:[],roadmaps:[{projectId:'r',sourceId:null,tasks:[],alternates:[],planIds:[]}],threads:[{id:'chat',title:'Deliver the feature',projectIds:['r'],workspacePaths:[],requestAt:'2020-01-01',responseAt:'2020-01-02',response:'Committed and pushed.',turnState:'finished',prs:['https://github.com/a/b/pull/1'],lastMessageAt:new Date().toISOString()}]};
state.delivery={checkedAt:new Date().toISOString(),repositories:[{repoId:'r',remote:'https://github.com/a/b',defaultBranch:'main',defaultCommit:'tip',checkedAt:new Date().toISOString(),stashes:0,limits:[],pullRequests:{'https://github.com/a/b/pull/1':{state:'included',branch:'fix',sha:'head'}},units:[{id:'r:fix',branch:'fix',sha:'head',state:'included',local:true,remoteExists:true,cleanup:true,pending:false,paths:[],worktreeCandidates:[],blockers:[],openPRs:[]}]}]};
render();`,context);
let html=elements.get('#content').innerHTML;
assert(html.includes('Recently completed'));assert(html.includes('On main'));assert(html.includes('Cleanup pending'));
assert(html.includes('Example &lt;Project&gt;'));assert(!html.includes('Needs a decision'));
vm.runInContext("state.view='overview';state.boardFilter='cleanup';render();",context);
html=elements.get('#content').innerHTML;
assert(html.includes('review candidates'));assert(html.includes('data-git-unit="r:fix"'));
vm.runInContext("showGitUnit('r:fix');",context);
assert(elements.get('#detailBody').innerHTML.includes('No deletion is performed'));
vm.runInContext("state.view='chats';state.query='no-match';render();",context);
assert(elements.get('#content').innerHTML.includes('No matching discussions'));
console.log('Delivery UI checks pass: verified completion, cleanup separation, escaped source text, read-only details and empty search.');
vm.runInContext("state.query='';state.view='chats';render();",context);
assert(!elements.get('#content').innerHTML.includes('data-cleanup-chat="chat"')); // History has no duplicate action queue.
vm.runInContext("state.data.threads[0].cwd='/missing/<checkout>';state.data.threads[0].assignedFolderExists=false;showChat('chat');",context);
html=elements.get('#detailBody').innerHTML;
assert(html.includes('No local checkout'));assert(html.includes('expected state after finished-session cleanup'));assert(!html.includes('Resolve its working-folder handoff'));assert(html.includes('Preview cleanup prompt'));assert(html.includes('/missing/&lt;checkout&gt;'));assert(!html.includes('/missing/<checkout>'));
vm.runInContext("cleanupChat('chat');",context);
assert(elements.get('#cleanupPrompt').value.includes('"chatId": "chat"'));
assert(elements.get('#detailBody').innerHTML.includes('readonly'));
assert(!elements.get('#detailBody').innerHTML.includes('send_message'));
console.log('Cleanup UI checks pass: per-row action, safe preview escaping and read-only draft fallback.');

// Reconciliation context must stay within the selected project and preserve uncertainty.
vm.runInContext(`
state.data.projects.push({id:'other',name:'Other project'});
state.data.threads.push({id:'other-chat',title:'Other private task',projectIds:['other']});
state.data.roadmaps[0].documentIds=['lowercase'];
state.data.documents=[{id:'lowercase',relative:'tasks.md',source:{path:'/project/tasks.md',branch:'feature',modified:true},sources:[{},{}]}];
state.delivery.repositories[0].defaultBranch='master';
showWorkflowPrompt('reconcile','r');`,context);
html=elements.get('#detailBody').innerHTML;
assert(html.includes('Deliver the feature'));assert(!html.includes('Other private task'));
assert(html.includes('readonly'));assert(!html.includes('data-triage'));
let draft=elements.get('#workflowPrompt').value;
assert(draft.includes('tasks.md'));assert(draft.includes('"versions": 2'));
assert(draft.includes('"defaultBranch": "master"'));assert(!draft.includes('Other project'));
assert(draft.includes('does not itself authorize commit'));assert(draft.includes('untrusted data'));
vm.runInContext("state.data.threads=state.data.threads.filter(t=>t.id!=='chat');showWorkflowPrompt('reconcile','r');",context);
assert(elements.get('#detailBody').innerHTML.includes('No local chat indexed'));
vm.runInContext('sourceInfo()',context);
assert(!elements.get('#detailBody').innerHTML.includes('own local metadata file'));
console.log('Workflow handoff checks pass: project isolation, ambiguous routing, draft-only controls, branch/version context and no personal tracking.');

// One primary action in the flyout; evidence cannot introduce more cleanup buttons.


vm.runInContext(`
state.data.threads=[{id:'chat',title:'Delivered unit',projectIds:['r'],workspacePaths:[],cwd:'/repo',response:'Committed and pushed.',requestAt:'2020-01-01',responseAt:'2020-01-02',turnState:'finished',prs:['https://github.com/a/b/pull/1'],lastMessageAt:new Date().toISOString(),link:'codex://threads/chat'}];
state.data.workspaces=[{path:'/repo',label:'Primary checkout',repoId:'r',branch:'main',chatIds:['chat'],fileCount:2,tip:['abc123'],ignoredCount:1}];
state.project='all';state.query='';state.view='overview';state.boardFilter='completed';render();showChat('chat');`,context);
html=elements.get('#detailBody').innerHTML;
assert.equal((html.match(/data-cleanup-chat=/g)||[]).length,1);
assert(html.includes('Evidence & session details'));
assert(!html.includes('Review leftover branches / worktrees'));
assert(!html.includes('Open in Codex</a>'));
assert(elements.get('#stats').innerHTML.includes('data-board-filter="completed"'));
assert(elements.get('#content').innerHTML.includes('Recently completed'));
assert(!elements.get('#content').innerHTML.includes('data-git-unit='));
vm.runInContext("state.boardFilter='resume';render();",context);
assert(!elements.get('#content').innerHTML.includes('Delivered unit'));
vm.runInContext("state.boardFilter='cleanup';render();",context);
assert(elements.get('#content').innerHTML.includes('data-git-unit="r:fix"'));
vm.runInContext("showCheckoutReview('/repo');",context);
assert(elements.get('#detailBody').innerHTML.includes('data-workflow-open="chat"'));
assert(!elements.get('#detailBody').innerHTML.includes('other-chat'));
assert(elements.get('#workflowPrompt').value.includes('Keep the primary checkout'));
vm.runInContext("state.data.workspaces[0].chatIds=[];showCheckoutReview('/repo');",context);
assert(elements.get('#detailBody').innerHTML.includes('No linked chat is indexed'));
assert(!elements.get('#detailBody').innerHTML.includes('data-workflow-open='));
vm.runInContext("showCheckoutReview('/not-indexed');",context);
assert(elements.get('#workflowPrompt').value.includes('"checkout": "/repo"'));
// Backdrop closes; interior clicks and drags beginning inside do not.
const dialog=elements.get('#detail');
const fire=(type,x,target=dialog)=>dialog.listeners[type].forEach(fn=>fn({target,clientX:x,clientY:100}));
dialog.open=true;fire('pointerdown',600);fire('click',600);assert(dialog.open);
fire('pointerdown',600);fire('click',100);assert(dialog.open);
fire('pointerdown',100);fire('click',100);assert.equal(dialog.open,false);
console.log('Queue interaction checks pass: filter isolation, one flyout action, checkout routing, unknown ownership and backdrop dismissal.');
