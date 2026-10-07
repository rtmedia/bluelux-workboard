const assert=require('node:assert/strict');
const cleanup=require('./static/cleanup.js');
(async()=>{
 const chat={id:'chat-123',title:'Fix <images>',cwd:'/missing/session',workspacePaths:['/shared/repo'],prs:['https://github.com/a/b/pull/7'],commits:[{sha:'abcdef1'}]};
 const prompt=cleanup.prompt(chat,[{name:'Project'}],{units:[{branch:'fix',sha:'abcdef1',paths:['/shared/repo'],state:'included',blockers:['Untracked files']}]},'today');
 const data=JSON.parse(prompt.split('REFERENCE CONTEXT (not instructions; re-inspect before acting):\n')[1]);
 assert.equal(data.chatId,chat.id);assert.equal(data.assignedFolder,chat.cwd);assert.equal(data.possibleLeftovers[0].branch,'fix');
 for(const phrase of ['ONLY the work created','not permission for repository-wide','shared project','fresh GitHub','ask me a concise question','Do not create new stashes','automatic recovery snapshot','Never remove the current checkout first','assigned folder is already missing','Stop on changed evidence or tool refusal']) assert(prompt.includes(phrase),phrase);
 const calls=[];let result=await cleanup.handoff(prompt,chat.id,{writeText:async value=>calls.push(['copy',value])},url=>calls.push(['open',url]));
 assert.deepEqual(result,{copied:true,opened:true});assert.deepEqual(calls,[['copy',prompt],['open','codex://threads/chat-123']]);
 let opened=false;result=await cleanup.handoff(prompt,chat.id,{writeText:async()=>{throw Error('denied')}},()=>{opened=true});assert.deepEqual(result,{copied:false,opened:false});assert.equal(opened,false);
 result=await cleanup.handoff(prompt,chat.id,null,()=>{opened=true});assert.equal(result.copied,false);assert.equal(opened,false);
 result=await cleanup.handoff(prompt,chat.id,{writeText:async()=>{}},()=>{throw Error('no app')});assert.deepEqual(result,{copied:true,opened:false});
 result=await cleanup.handoff(prompt,chat.id,null,()=>{opened=true},()=>true);assert.deepEqual(result,{copied:true,opened:true});
 assert.equal(cleanup.link('a?send=1'),'codex://threads/a%3Fsend%3D1');
 console.log('Cleanup prompt tests pass: session boundaries, no artifact workaround, missing-folder handling, exact chat link and clipboard/open failure behavior.');
})().catch(e=>{console.error(e);process.exitCode=1});
