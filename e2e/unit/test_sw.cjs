const fs=require('fs'),vm=require('vm'),assert=require('assert');
const scope='https://example.test/esstu-schedule/', prefix=`esstu-pwa:${scope}:`;
const handlers={},stores=new Map(),deleted=[],timeouts=[],installRequests=[];
let offline=false,status=200,failPut=false,fetches=0,skipped=false,deferred=null;
const notifications=[],backgroundJobs=[];
const key=request=>new URL(typeof request==='string'?request:request.url,scope).href;
function store(name){
  if(!stores.has(name)){
    const entries=new Map();
    stores.set(name,{
      async match(request,options={}){
        const url=key(request);
        const found=[...entries].find(([candidate])=>options.ignoreSearch?candidate.split('?')[0]===url.split('?')[0]:candidate===url);
        return found?.[1].clone();
      },
      async put(request,response){if(failPut)throw Error('quota');entries.set(key(request),response.clone());},
      async delete(request){return entries.delete(key(request));},
      async keys(){return [...entries.keys()].map(url=>new Request(url));},
      async addAll(assets){for(const request of assets){assert(request instanceof Request);assert.equal(request.cache,'reload');assert(request.url.startsWith(scope));installRequests.push(request);await this.put(request,new Response('installed shell'));}}
    });
  }
  return stores.get(name);
}
const context={self:{addEventListener:(name,fn)=>handlers[name]=fn,location:{origin:new URL(scope).origin},registration:{scope},clients:{claim:async()=>{},matchAll:async()=>[{postMessage:message=>notifications.push(message)}]},skipWaiting:async()=>{skipped=true}},
  caches:{open:async name=>store(name),keys:async()=>[...stores.keys()],delete:async name=>{deleted.push(name);return stores.delete(name);}},
  fetch:async(request,options)=>{fetches++;assert.equal(options.cache,'reload');if(offline)throw Error('offline');if(deferred)return deferred;return new Response('network',{status});},
  Request,Response,Headers,URL,setTimeout:(fn,ms)=>setTimeout(fn,ms===3500?10:ms),clearTimeout,AbortSignal:{timeout:ms=>{timeouts.push(ms);return AbortSignal.timeout(ms);}},console:{warn(){}}};
vm.createContext(context);vm.runInContext(fs.readFileSync('static/sw.js','utf8'),context);
async function lifecycle(name,event={}){let job;handlers[name]({...event,waitUntil:p=>job=p});await job;}
async function request(path,options={}){let result;handlers.fetch({request:new Request(new URL(path,scope),options),waitUntil:p=>backgroundJobs.push(p),respondWith:p=>result=p});return result;}
(async()=>{
  const json=subject=>new Response(JSON.stringify({mode:'student',weeks:{},subject}),{headers:{'Content-Type':'application/json'}});
  const legacy=store('esstu-live-v1');
  await legacy.put('api/schedule?group=A',json('A'));
  await legacy.put('api/schedule?group=B',json('B'));
  await legacy.put('https://example.test/another-app/api/private',json('other'));
  const clean=store('esstu-live-v2');await clean.put('api/schedule?group=C',json('C'));
  const v1=store(`${prefix}data-v1`);await v1.put('api/teacher',new Response(JSON.stringify({mode:'teacher',weeks:{}})));
  const corrupt=store('esstu-live-broken');await corrupt.put('api/broken',new Response('not JSON'));
  store(`${prefix}old-shell`);store('another-app');store('esstu-pwa:another-scope:shell');
  await lifecycle('install');assert(!skipped,'update waits for the user');assert(installRequests.length>10);
  await lifecycle('activate');
  assert(deleted.includes('esstu-live-v2'));assert(deleted.includes(`${prefix}data-v1`));assert(deleted.includes(`${prefix}old-shell`));
  assert(stores.has('esstu-live-v1'),'shared cache retained');assert(stores.has('esstu-live-broken'),'failed migration retained');
  assert(stores.has('another-app'));assert(stores.has('esstu-pwa:another-scope:shell'));
  const data=store(`${prefix}data-v2`);
  assert(!(await data.match('https://example.test/another-app/api/private')));
  assert.equal((await (await data.match('api/teacher')).json()).identity_ambiguous,true);
  offline=true;
  const a=await request('api/schedule?group=A');assert.equal((await a.json()).subject,'A');assert.equal(a.headers.get('X-ESSTU-Cache'),'offline');assert.equal(timeouts.length,0,'cached request is never aborted by the response deadline');
  assert.equal((await (await request('api/schedule?group=B')).json()).subject,'B');
  assert.equal((await request('api/schedule?group=missing')).status,503);assert.equal(timeouts.at(-1),12000);
  const before=fetches;
  assert.equal(await (await request('modern.js')).text(),'installed shell');assert.equal(fetches,before);
  assert.equal(await request('avatars/photo.webp'),undefined);assert.equal(await request('unlisted.js'),undefined);
  offline=false;failPut=true;
  assert.equal(await (await request('api/schedule?group=A')).text(),'network','quota cannot hide network success');
  assert.equal((await (await data.match('api/schedule?group=A')).json()).subject,'A','quota retains old copy');
  failPut=false;status=404;
  assert.equal((await request('api/schedule?group=A')).status,404,'do not resurrect deleted resources');
  status=503;const fallback=await request('api/schedule?group=A');assert.equal(fallback.headers.get('X-ESSTU-Cache'),'server-error');assert.equal((await fallback.json()).subject,'A');
  status=200;assert.equal(await (await request('api/schedule?group=A')).text(),'network');
  await lifecycle('activate');offline=true;
  assert.equal(await (await request('api/schedule?group=A')).text(),'network','reactivation preserves data');
  offline=false;
  await lifecycle('message',{data:{type:'PROTECT_DATA',urls:[new URL('api/schedule?group=A',scope).href]}});
  let resolveSlow;deferred=new Promise(resolve=>resolveSlow=resolve);
  const slow=await request('api/schedule?group=A');assert.equal(slow.headers.get('X-ESSTU-Cache'),'refreshing');assert.equal(await slow.text(),'network');
  resolveSlow(new Response('slow fresh data'));await Promise.all(backgroundJobs);deferred=null;
  assert.equal(await (await data.match('api/schedule?group=A')).text(),'slow fresh data');assert(notifications.some(message=>message.type==='DATA_UPDATED'));
  await Promise.all(Array.from({length:205},(_,i)=>request('api/bounded/'+i)));
  assert.equal((await data.keys()).length,200,'concurrent writes respect the data entry limit');assert(await data.match('api/schedule?group=A'),'protected current group survives FIFO eviction');
  assert.equal(await request('https://example.test/outside/api/data'),undefined);
  assert.equal(await request('api/meta',{method:'POST'}),undefined);
  await lifecycle('message',{data:{type:'SKIP_WAITING'}});assert(skipped);
  console.log('Worker: reload install, allowlist, scope-safe migration, quota recovery, bounded schema-v2 data, background refresh after 3.5s, 5xx/offline and manual activation OK');
})().catch(error=>{console.error(error);process.exitCode=1;});
