const fs=require('fs'),vm=require('vm'),assert=require('assert');
const ui={Date,document:{addEventListener(){}},displayDate:date=>new Date(date).toISOString()};
vm.createContext(ui);vm.runInContext(fs.readFileSync('static/accessibility.js','utf8'),ui);
ui.now=Date.parse('2026-10-16T08:00:00+08:00');
assert.equal(vm.runInContext('relativeChecked("2026-10-16T06:00:00+08:00",now)',ui),'Проверено 2 ч назад');
assert.equal(vm.runInContext('relativeChecked(null,now)',ui),'Дата проверки неизвестна');
assert(vm.runInContext('daySourceText({source_file:"bakalavriat/1.htm"},{cached:true},true)',ui).startsWith('Офлайн-копия'));

// Exercise the actual notification script with an in-memory GitHub API.
const workflow=fs.readFileSync('.github/workflows/sync.yml','utf8').replace(/\r\n/g,'\n');
const script=workflow.split('          script: |\n')[1].split('\n').map(line=>line.slice(12)).join('\n');
async function notification(result,exists){
  const calls=[];const api={};
  for(const action of ['update','create'])api[action]=async data=>calls.push({action,...data});
  api.listForRepo=()=>{};
  const github={paginate:async()=>exists?[{number:8,title:'Автоматическая синхронизация расписания: ошибка'}]:[],rest:{issues:api}};
  await new Function('github','context','process',`return (async()=>{${script}})()`)(github,{repo:{owner:'test',repo:'test'},runId:123},{env:{SYNC_RESULT:result}});
  return calls;
}
(async()=>{
  const ci=fs.readFileSync('.github/workflows/ci.yml','utf8').replace(/\r\n/g,'\n');
  const restore=ci.split('          script: |\n')[1].split('\n      - uses:')[0].split('\n').map(line=>line.slice(12)).join('\n');
  async function snapshot(count,hasArtifact){
    const outputs={},warnings=[];
    const github={
      paginate:async()=>Array.from({length:count},(_,id)=>({id})),
      rest:{actions:{
        listWorkflowRuns(){},
        listWorkflowRunArtifacts:async({run_id})=>({data:{artifacts:hasArtifact&&run_id===count-1?[{name:'source-snapshot',expired:false}]:[]}})
      }}
    };
    await new Function('github','context','core',`return (async()=>{${restore}})()`)(github,{repo:{owner:'test',repo:'test'}},{setOutput:(name,value)=>outputs[name]=value,warning:text=>warnings.push(text)});
    return {outputs,warnings};
  }
  assert.equal((await snapshot(12,true)).outputs.run_id,'11','retained snapshots beyond ten runs are found');
  assert.equal((await snapshot(12,false)).warnings.length,1,'fallback to repository data is visible');
  assert.equal((await notification('failure',false))[0].action,'create');
  assert.equal((await notification('failure',true))[0].action,'update');
  assert.equal((await notification('success',true))[0].state,'closed');
  assert.deepEqual(await notification('success',false),[]);
  console.log('Source age, offline label, failure notification deduplication and recovery OK');
})().catch(error=>{console.error(error);process.exitCode=1});
