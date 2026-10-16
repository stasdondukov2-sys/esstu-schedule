const fs=require('fs'),vm=require('vm'),assert=require('assert');
const scope='https://example.test/esstu-schedule/', prefix=`esstu-pwa:${scope}:`;
const handlers={},stores=new Map(),deleted=[];
let offline=false,status=200,failPut=false,fetches=0,skipped=false;
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
      async put(request,response){if(failPut)throw Error('quota');entries.set(key(request),response.clone())},
      async keys(){return [...entries.keys()].map(url=>new Request(url))},
      async addAll(assets){for(const asset of assets){assert(asset.startsWith('./'));await this.put(asset,new Response('installed shell'))}}
    });
  }
  return stores.get(name);
}
const context={self:{addEventListener:(name,fn)=>handlers[name]=fn,location:{origin:new URL(scope).origin},registration:{scope},clients:{claim:async()=>{}},skipWaiting:async()=>{skipped=true}},
  caches:{open:async name=>store(name),keys:async()=>[...stores.keys()],delete:async name=>{deleted.push(name);return stores.delete(name)}},
  fetch:async()=>{fetches++;if(offline)throw Error('offline');return new Response('network',{status})},
  Response,Headers,URL,AbortSignal,console:{warn(){}}};
vm.createContext(context);vm.runInContext(fs.readFileSync('static/sw.js','utf8'),context);
async function lifecycle(name,event={}){let job;handlers[name]({...event,waitUntil:p=>job=p});await job}
async function request(path,options={}){let result;handlers.fetch({request:new Request(new URL(path,scope),options),respondWith:p=>result=p});return result}
(async()=>{
  const legacy=store('esstu-live-v1');
  await legacy.put('api/schedule?group=A',new Response('A'));
  await legacy.put('api/schedule?group=B',new Response('B'));
  await legacy.put('https://example.test/another-app/api/private',new Response('other'));
  store(`${prefix}old-shell`);store('another-app');store('esstu-pwa:another-scope:shell');
  await lifecycle('install');assert(!skipped,'update waits for the user');
  await lifecycle('activate');assert.deepEqual(deleted,[`${prefix}old-shell`]);
  const data=store(`${prefix}data-v1`);
  assert(!(await data.match('https://example.test/another-app/api/private')));
  offline=true;
  assert.equal(await (await request('api/schedule?group=A')).text(),'A');
  assert.equal(await (await request('api/schedule?group=B')).text(),'B');
  assert.equal((await request('api/schedule?group=C')).status,503);
  assert.equal((await request('api/schedule?group=A')).headers.get('X-ESSTU-Cache'),'offline');
  const before=fetches;
  assert.equal(await (await request('modern.js')).text(),'installed shell');assert.equal(fetches,before);
  offline=false;failPut=true;
  assert.equal(await (await request('api/new.json')).text(),'network','quota cannot hide network success');
  failPut=false;status=404;
  assert.equal((await request('api/schedule?group=A')).status,404,'do not resurrect deleted resources');
  status=503;assert.equal(await (await request('api/schedule?group=A')).text(),'A');
  status=200;assert.equal(await (await request('api/schedule?group=A')).text(),'network');
  await lifecycle('activate');offline=true;
  assert.equal(await (await request('api/schedule?group=A')).text(),'network','reactivation preserves data');
  assert.equal(await request('https://example.test/outside/api/data'),undefined);
  assert.equal(await request('api/meta',{method:'POST'}),undefined);
  await lifecycle('message',{data:{type:'SKIP_WAITING'}});assert(skipped);
  console.log('Worker: shell isolation, persistent data migration, exact queries, freshness, quota errors, 404/503 and manual activation OK');
})().catch(error=>{console.error(error);process.exitCode=1});
