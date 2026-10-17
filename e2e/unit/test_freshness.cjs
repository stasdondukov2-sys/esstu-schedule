const assert=require('assert');
const {freshnessProblem,monitor}=require('../../scripts/freshness.cjs');
const now=Date.parse('2026-10-17T12:00:00+08:00');
const fresh={generated_at:new Date(now).toISOString(),source_checked_at_latest:new Date(now-3600000).toISOString(),group_check_dates:{'zo1/1':new Date(now-3600000).toISOString()}};
assert.equal(freshnessProblem(fresh,now),'');
assert(freshnessProblem({...fresh,group_check_dates:{a:fresh.generated_at,b:'2026-10-15T00:00:00Z'}},now).includes('1/2 (50.0%)'));
assert(freshnessProblem({...fresh,group_check_dates:{a:null}},now).includes('0/1'));
assert(freshnessProblem({...fresh,generated_at:'2026-10-16T12:00:00+08:00'},now).includes('Сборка: более 12 часов'));
assert(freshnessProblem({...fresh,source_checked_at_latest:'2026-10-16T12:00:00+08:00'},now).includes('Проверка источников: более 12 часов'));
assert(freshnessProblem({},now).includes('дата неизвестна'));
assert(freshnessProblem({...fresh,generated_at:'2026-10-18T12:00:00+08:00'},now).includes('дата в будущем'));
async function check(payload,existing,networkError=false){
  const calls=[];
  const api={listForRepo(){},create:async data=>calls.push({action:'create',...data}),update:async data=>calls.push({action:'update',...data})};
  const github={rest:{issues:api},paginate:async()=>existing?[{number:7,title:'Расписание: выгрузка устарела'}]:[]};
  await monitor({github,context:{repo:{owner:'test',repo:'schedule'},runId:123},now,
    fetchImpl:async(url,options)=>{assert(url.includes('?freshness='));assert.equal(options.cache,'no-store');if(networkError)throw Error('unavailable');return {ok:true,json:async()=>payload};}});
  return calls;
}
(async()=>{
  assert.deepEqual(await check(fresh,false),[]);
  assert.equal((await check({},false))[0].action,'create');
  assert.equal((await check({},true))[0].action,'update');
  assert.equal((await check(fresh,true))[0].state,'closed');
  assert((await check(fresh,false,true))[0].body.includes('unavailable'));
  console.log('Freshness: 12-hour threshold, source age independent of build age, unknown/future timestamps, issue deduplication and recovery OK');
})().catch(error=>{console.error(error);process.exitCode=1;});
