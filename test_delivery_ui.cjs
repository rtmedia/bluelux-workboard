const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const elements=new Map();
function element(){return {innerHTML:'',textContent:'',dataset:{},classList:{toggle(){}},setAttribute(){},addEventListener(){},append(){},showModal(){this.open=true},close(){this.open=false}};}
const document={querySelector:s=>{if(!elements.has(s))elements.set(s,element());return elements.get(s)},querySelectorAll:()=>[],createElement:element,body:element(),addEventListener(){}};
const context=vm.createContext({document,window:{addEventListener(){}},fetch:()=>new Promise(()=>{}),setInterval(){},setTimeout(){},clearTimeout(){},URLSearchParams,console});
vm.runInContext(fs.readFileSync('static/focus.js','utf8'),context);
vm.runInContext(fs.readFileSync('static/app.js','utf8'),context);
vm.runInContext(`
state.data={checkedAt:new Date().toISOString(),projects:[{id:'r',name:'Example <Project>',core:true}],repositories:[{id:'r',stashes:[]}],documents:[],workspaces:[],roadmaps:[{projectId:'r',sourceId:null,tasks:[],alternates:[],planIds:[]}],threads:[{id:'chat',title:'Deliver the feature',projectIds:['r'],workspacePaths:[],requestAt:'2020-01-01',responseAt:'2020-01-02',response:'Committed and pushed.',turnState:'finished',prs:['https://github.com/a/b/pull/1'],lastMessageAt:new Date().toISOString()}]};
state.delivery={checkedAt:new Date().toISOString(),repositories:[{repoId:'r',remote:'https://github.com/a/b',defaultBranch:'main',defaultCommit:'tip',checkedAt:new Date().toISOString(),stashes:0,limits:[],pullRequests:{'https://github.com/a/b/pull/1':{state:'included',branch:'fix',sha:'head'}},units:[{id:'r:fix',branch:'fix',sha:'head',state:'included',local:true,remoteExists:true,cleanup:true,pending:false,paths:[],worktreeCandidates:[],blockers:[],openPRs:[]}]}]};
render();`,context);
let html=elements.get('#content').innerHTML;
assert(html.includes('Recently completed'));assert(html.includes('On main'));assert(html.includes('Cleanup pending'));
assert(html.includes('Example &lt;Project&gt;'));assert(!html.includes('Needs a decision'));
vm.runInContext("state.view='cleanup';render();",context);
html=elements.get('#content').innerHTML;
assert(html.includes('review candidates'));assert(html.includes('data-git-unit="r:fix"'));
vm.runInContext("showGitUnit('r:fix');",context);
assert(elements.get('#detailBody').innerHTML.includes('No deletion is performed'));
vm.runInContext("state.view='chats';state.query='no-match';render();",context);
assert(elements.get('#content').innerHTML.includes('No matching discussions'));
console.log('Delivery UI checks pass: verified completion, cleanup separation, escaped source text, read-only details and empty search.');
