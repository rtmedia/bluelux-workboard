const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const elements=new Map();
function element(){return {style:{},remove(){},listeners:{},closest(){return null},getBoundingClientRect(){return {left:500,right:1000,top:0,bottom:800}},innerHTML:'',textContent:'',dataset:{},classList:{toggle(){}},setAttribute(){},addEventListener(type,fn){(this.listeners[type]??=[]).push(fn)},append(){},focus(){},select(){},showModal(){this.open=true},close(){this.open=false}};}
const document={querySelector:s=>{if(!elements.has(s))elements.set(s,element());return elements.get(s)},querySelectorAll:()=>[],createElement:element,body:element(),addEventListener(){}};
const context=vm.createContext({document,window:{addEventListener(){},matchMedia(){return {matches:false,addEventListener(){}}}},fetch:()=>new Promise(()=>{}),setInterval(){},setTimeout(){},clearTimeout(){},URLSearchParams,console});
vm.runInContext(fs.readFileSync('static/signals.js','utf8'),context);
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
assert(elements.get('#content').innerHTML.includes('No matching chats'));
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


// Use the real scenario shape: an old handoff plus a newer selected file marked DONE.
vm.runInContext(`
state.data.documents=[{id:'taskdoc',relative:'TASKS.md',source:{path:'/newer/TASKS.md',branch:'feature',committedAt:1790899200,modified:false},sources:[{workspace:'/newer',path:'/newer/TASKS.md',branch:'feature'}],taskCounts:{done:1}}];
state.data.roadmaps[0]={projectId:'r',sourceId:'taskdoc',alternates:['taskdoc'],planIds:[],tasks:[{key:'DESIGN3',title:'DESIGN3 audit',status:'done',checks:[]}]};
state.data.threads=[{id:'old',title:'Continue DESIGN3 audit',projectIds:['r'],workspacePaths:['/repo'],cwd:'/repo',requestAt:'2026-05-16',responseAt:'2026-05-17',response:'DESIGN3 still needs the broader QA pass.',turnState:'finished',prs:[],lastMessageAt:'2026-05-17',link:'codex://threads/old'}];
state.data.workspaces[0].primary=true;state.data.workspaces[0].chatIds=['old'];state.data.workspaces[0].files=[];state.data.workspaces[0].ignoredPaths=[];
state.project='r';state.view='overview';state.boardFilter='review';render();showChat('old');`,context);
html=elements.get('#detailBody').innerHTML;
assert(html.includes('Task closed in ledger'));assert(html.includes('Open history ↗'));assert(!html.includes('>Continue ↗'));assert(!html.includes('Copies a prompt and opens this chat.'));
assert(html.includes('DESIGN3 · Done'));assert(html.includes(new Date(1790899200000).toLocaleString()));assert(!html.includes('58720')); assert(html.includes('/newer/TASKS.md'));
assert(html.includes('Shared primary checkout — keep'));assert(html.includes('Current branch: main'));
assert(!html.includes('Delivery verified'));
vm.runInContext("state.boardFilter='resume';render();",context);
assert(!elements.get('#content').innerHTML.includes('Continue DESIGN3 audit'));
vm.runInContext("state.view='workspaces';render();",context);
html=elements.get('#content').innerHTML;
assert(html.includes('Keep primary checkout'));assert(html.includes('Reconcile local changes')||html.includes('Review primary checkout'));
assert(html.includes('historical chat links'));assert(html.includes('Current branch'));
assert(html.includes('0 open tasks = 0 in progress / blocked + 0 planned'));
assert(elements.get('#projects').innerHTML.includes('0 tasks'));
vm.runInContext("state.workflowDraft=handoffPrompt('reconcile-chat',state.data.threads[0],null);",context);
draft=vm.runInContext('state.workflowDraft',context);
assert(draft.startsWith('Reconcile the current status'));assert(!draft.startsWith('Pick up'));
assert(draft.includes('DESIGN3'));assert(draft.includes('/newer/TASKS.md'));assert(draft.includes('not necessarily the completion date'));
// Version browsing must work independently of the currently selected workspace.
assert(vm.runInContext("versionsBody('r')",context).includes('/newer/TASKS.md'));
console.log('Decision UI checks pass: source-labelled counts, DESIGN3 reconciliation, primary/current-branch distinctions, scoped prompt and version browsing.');

// A fresher local scan protects shared work even before the next delivery scan.
vm.runInContext(`state.data.threads[0].response='Done.';state.data.threads[0].prs=['https://github.com/o/r/pull/1'];state.delivery={repositories:[{repoId:'r',remote:'https://github.com/o/r',defaultCommit:'main',checkedAt:new Date().toISOString(),pullRequests:{'https://github.com/o/r/pull/1':{state:'included',sha:'tip',branch:'feature'}},units:[{state:'included',sha:'tip',branch:'feature',cleanup:true,paths:['/repo']}]}]};`,context);
assert(vm.runInContext('sessionAction(state.data.threads[0])',context).includes('Reconcile related local work'));
assert(!vm.runInContext('sessionAction(state.data.threads[0])',context).includes('Clean up session'));

// Old unlinked ambiguity belongs in History, not an ever-growing action queue.
vm.runInContext(`state.data.threads.push({id:'historical',title:'Old question',projectIds:['r'],workspacePaths:[],request:'What is this?',response:'Here is an explanation.',responseAt:'2026-01-01',lastMessageAt:'2026-01-01'});`,context);
assert(!vm.runInContext('discussionGroups().review.some(t=>t.id==="historical")',context));
assert(vm.runInContext('threads().some(t=>t.id==="historical")',context));

vm.runInContext(`state.delivery.repositories[0].units.push({state:'included',sha:'tip',branch:'feature',cleanup:true,paths:[]});showChat('old');`,context);
assert(elements.get('#detailBody').innerHTML.includes('Reconcile related local work'));
assert(!elements.get('#detailBody').innerHTML.includes('Preview cleanup prompt'));
assert(!elements.get('#detailBody').innerHTML.includes('Cleanup pending'));

// Historical follow-up stays searchable but never offers an automatic Continue.
vm.runInContext(`state.data.threads.push({id:'past-followup',title:'Past follow-up',projectIds:['r'],workspacePaths:[],requestAt:'2020-01-01',responseAt:'2020-01-02',lastMessageAt:'2020-01-02',response:'Still needs a rethink.',link:'codex://threads/past-followup'});state.view='overview';state.boardFilter='resume';render();`,context);
assert(!elements.get('#content').innerHTML.includes('Past follow-up'));
vm.runInContext(`state.view='chats';render();showChat('past-followup');`,context);
assert(elements.get('#content').innerHTML.includes('Past follow-up'));
assert(elements.get('#detailBody').innerHTML.includes('Historical discussion'));
assert(elements.get('#detailBody').innerHTML.includes('Open history ↗'));
assert(!elements.get('#detailBody').innerHTML.includes('>Continue ↗'));
// Recent contradictory evidence still requests source reconciliation.
vm.runInContext(`state.data.threads[0].response='DESIGN3 still needs QA';state.data.threads[0].responseAt=new Date().toISOString();state.data.threads[0].prs=[];showChat('old');`,context);
assert(elements.get('#detailBody').innerHTML.includes('Reconcile status'));
console.log('Historical UI checks pass: discoverable history, no Continue for old prose, recent conflicts still reconciled.');

// Compact mode keeps current evidence, scoped work and expanded navigation intact.
vm.runInContext(`state.data.roadmaps.forEach(r=>r.warnings=[]);compactViewport.matches=true;state.project='r';state.view='overview';state.boardFilter='all';state.query='';render();`,context);
html=elements.get('#content').innerHTML;
assert(html.includes('companion-board'));assert(html.includes('Projects'));
assert(!html.includes('Other private task'));assert(!html.includes('project-source-summary'));
assert.equal(elements.get('#compactProject').value,'r');
vm.runInContext(`state.fullView=true;render();`,context);
assert(!elements.get('#content').innerHTML.includes('companion-board'));
assert(elements.get('#content').innerHTML.includes('Workboard filters'));
vm.runInContext(`state.fullView=false;state.view='roadmap';render();`,context);
assert(!elements.get('#content').innerHTML.includes('companion-board'));
assert(elements.get('#content').innerHTML.includes('Task status'));
vm.runInContext(`compactViewport.matches=false;state.view='overview';render();`,context);
assert(!elements.get('#content').innerHTML.includes('companion-board'));
assert(elements.get('#content').innerHTML.includes('Workboard filters'));
console.log('Companion checks pass: scoped overview, source-backed tasks, roadmap access and expanded-view restoration.');

vm.runInContext(`
state.project='all';state.query='';state.view='overview';state.boardFilter='all';
state.data.threads=[{id:'signal',title:'Approval <needed>',cwd:'/repo',projectIds:['r'],workspacePaths:[],requestAt:new Date(Date.now()-120000).toISOString(),responseAt:new Date().toISOString(),response:'Remaining: this needs your approval.',lastMessageAt:new Date().toISOString(),turnState:'finished',telemetry:{observedAt:new Date().toISOString(),lastTokens:800,contextWindow:1000,totalTokens:9999,windows:[]}}];
compactViewport.matches=true;state.fullView=false;render();`,context);
html=elements.get('#content').innerHTML;
assert(html.includes('Needs you'));assert(html.includes('Approval &lt;needed&gt;'));
assert(html.includes('data-signal-git'));assert(html.includes('data-pause'));
vm.runInContext("showSessions();",context);
html=elements.get('#detailBody').innerHTML;
assert(html.includes('80% context estimate'));assert(html.includes('Cost unknown'));
assert(html.includes('Allowance and resets unknown'));
vm.runInContext("showHandoff('signal');",context);
assert(elements.get('#workflowPrompt').value.includes('Do not commit, push, deploy, delete, archive or start another session'));
assert(elements.get('#detailBody').innerHTML.includes('readonly'));
vm.runInContext("state.paused=true;render();",context);
assert(elements.get('#content').innerHTML.includes('Updates paused in this window'));
console.log('Companion signals UI passes: attention, escaping, unknown allowance/cost, estimated context and draft-only handoff.');
const demo=JSON.parse(require('node:child_process').execFileSync('python3',['-c','import demo,json;print(json.dumps(demo.snapshot()[0]))'],{encoding:'utf8'}));
context.demoFixture=demo;
vm.runInContext("state.data=demoFixture;state.delivery={repositories:[]};state.project='all';state.query='';state.paused=false;for(const view of ['overview','roadmap','plans','chats','workspaces','instructions']){state.view=view;render()}",context);
assert(elements.get('#content').innerHTML.includes('Global instructions'));
console.log('Synthetic demo renders all six views without host data.');
vm.runInContext("state.view='overview';state.fullView=false;compactViewport.matches=true;render();",context);
html=elements.get('#content').innerHTML;
assert(html.includes('visual-metrics'));assert(html.includes('visual-chat'));assert(html.includes('visual-ring'));
assert(html.includes('Resets in'));assert(!html.includes('Context used:'));assert(html.includes('Allowance left: 72 percent'));
assert(html.includes('GitHub coverage incomplete; 0 open PRs observed'));assert(html.includes('Context estimate: unknown'));
assert(html.includes('aria-label="Hide screen"'));assert(!html.includes('Remaining: this needs your approval before implementation.'));
assert(vm.runInContext("visualBar(null,'Missing')",context).includes('Missing: unknown'));
assert(vm.runInContext("visualBar(0,'Zero')",context).includes('Zero: 0 percent'));
assert(vm.runInContext("visualBar(50,'Old','blue',true)",context).includes('stale snapshot'));
console.log('Visual companion checks pass: measured bars, unknown versus zero, stale labels, compact cards and accessible icon controls.');

(async()=>{
 const copied=[];context.navigator={clipboard:{writeText:async text=>copied.push(text)}};
 context.window.location={href:'unchanged'};document.execCommand=()=>false;
 vm.runInContext("state.detail='original';",context);
 await vm.runInContext("directWorkflowHandoff('continue','demo-approval')",context);
 assert.equal(context.window.location.href,'codex://threads/demo-approval');
 assert.equal(vm.runInContext('state.detail',context),'original');
 assert(copied[0].includes('Pick up the work in this exact chat'));
 context.window.location.href='unchanged';context.navigator.clipboard.writeText=async()=>{throw Error('denied')};
 await vm.runInContext("directWorkflowHandoff('continue','demo-approval')",context);
 assert.equal(context.window.location.href,'unchanged');
 assert.equal(vm.runInContext('state.detail',context),'workflow-prompt');
 assert(elements.get('#workflowStatus').textContent.includes('Clipboard unavailable'));
 assert(elements.get('#workflowPrompt').value.includes('demo-approval'));
 console.log('Direct handoff passes: copy before same-window deep link, no success preview, and no navigation after clipboard denial.');
})().catch(e=>{console.error(e);process.exitCode=1});

vm.runInContext(`state.query='';state.data.threads[0].telemetry={observedAt:new Date().toISOString(),windows:[{usedPercent:30,minutes:300,resetsAt:Date.now()/1000+3600},{usedPercent:90,minutes:10080,resetsAt:Date.now()/1000+7200}]};`,context);
html=vm.runInContext('visualUsage(1)',context);
assert(html.includes('10%'));assert(html.includes('Resets in'));assert(html.includes('7d window'));assert(!html.includes('Context used'));
