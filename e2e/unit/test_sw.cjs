const fs=require('fs'),vm=require('vm'),assert=require('assert');
const handlers={},deleted=[];
let response=new Response('{"ok":true}',{headers:{'Content-Type':'application/json'}}),offline=false;
const cache={match:async()=>response.clone(),put:async()=>{},addAll:async assets=>{assert(assets.every(path=>path.startsWith('./')))}};
const context={self:{addEventListener:(name,fn)=>handlers[name]=fn,location:{origin:'https://example.test'},registration:{scope:'https://example.test/esstu-schedule/'},clients:{claim:async()=>{}},skipWaiting(){context.skipped=true}},
 caches:{open:async()=>cache,keys:async()=>['esstu-live-v1','another-app'],delete:async key=>deleted.push(key)},
 fetch:async()=>{if(offline)throw Error();return response.clone()},Response,Headers,URL,AbortSignal};
vm.createContext(context);vm.runInContext(fs.readFileSync('static/sw.js','utf8'),context);
(async()=>{
 let job;handlers.install({waitUntil:p=>job=p});await job;assert(!context.skipped,'update waits for the user');
 handlers.activate({waitUntil:p=>job=p});await job;assert.deepEqual(deleted,['esstu-live-v1']);
 let result;offline=true;
 handlers.fetch({request:new Request('https://example.test/esstu-schedule/api/groups/bakalavriat.json'),respondWith:p=>result=p});
 const cached=await result;assert.equal(cached.headers.get('X-ESSTU-Cache'),'offline');assert.equal((await cached.json()).ok,true);
 let intercepted=false;handlers.fetch({request:new Request('https://example.test/api/meta',{method:'POST'}),respondWith:()=>intercepted=true});assert(!intercepted);
 handlers.message({data:{type:'SKIP_WAITING'}});assert(context.skipped);
 console.log('Worker: scoped assets, manual update, own-cache cleanup, offline marker and POST bypass OK');
})().catch(error=>{console.error(error);process.exitCode=1});
