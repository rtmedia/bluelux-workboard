const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
(async () => {
  const handlers = {}, added = [], matched = [], deleted = [];
  const recovery = {body:'Recovery screen'};
  const origin = 'http://127.0.0.1:43127';
  const context = {URL, Promise,
    self:{location:{origin}, addEventListener:(name,cb)=>handlers[name]=cb,skipWaiting:async()=>{},clients:{claim:async()=>{}}},
    caches:{open:async()=>({addAll:async paths=>added.push(...paths)}), keys:async()=>['unrelated-cache','workboard-recovery-old','workboard-recovery-v1','workboard-recovery-v2'],delete:async key=>deleted.push(key),match:async path=>{matched.push(path);return recovery}},
    fetch:async()=>{throw Error('Server stopped');}};
  vm.runInNewContext(fs.readFileSync('static/sw.js','utf8'),context);
  let done;
  handlers.install({waitUntil:p=>done=p});await done;
  assert(added.includes('/offline.html'));assert(!added.some(p=>p.startsWith('/api/')));
  handlers.activate({waitUntil:p=>done=p});await done;
  assert.deepEqual(deleted,['workboard-recovery-old','workboard-recovery-v1']);
  for(const request of [
    {url:origin+'/api/state',method:'GET',mode:'cors'},
    {url:origin+'/api/refresh',method:'POST',mode:'cors'},
    {url:'https://example.org/',method:'GET',mode:'navigate'},
    {url:origin+'/app.js',method:'GET',mode:'cors'}]) {
    let handled=false;handlers.fetch({request,respondWith:()=>handled=true});assert.equal(handled,false);
  }
  handlers.fetch({request:{url:origin+'/',method:'GET',mode:'navigate'},respondWith:p=>done=p});
  assert.equal(await done,recovery);assert.deepEqual(matched,['/offline.html']);
  const manifest=JSON.parse(fs.readFileSync('static/manifest.webmanifest','utf8'));
  assert.equal(manifest.display,'standalone');assert.equal(manifest.start_url,'/');
  for(const size of [192,512]) {
    const icon=manifest.icons.find(i=>i.sizes===`${size}x${size}`);assert(icon);
    const png=fs.readFileSync('static'+icon.src);
    assert.equal(png.readUInt32BE(16),size);assert.equal(png.readUInt32BE(20),size);
  }
  console.log('PWA checks pass: manifest/icons, recovery, network-only API and scoped cache cleanup.');
})().catch(error=>{console.error(error);process.exitCode=1});
