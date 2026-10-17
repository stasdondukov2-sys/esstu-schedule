const fs=require('fs'),vm=require('vm'),assert=require('assert'),{spawnSync}=require('child_process');
const dates=[];
for(let year=2020;year<=2032;year++)for(const [month,day]of[[1,1],[7,31],[8,1],[8,25],[8,30],[8,31],[9,1],[9,2],[9,3],[9,7],[12,31]])for(const hour of[0,12,23])dates.push([year,month,day,hour]);
const python=spawnSync(process.env.PYTHON_CMD || 'python',['-c','import json,sys;from datetime import datetime;from esstu_schedule.parser import get_week_num;print(json.dumps([get_week_num(datetime(*row)) for row in json.load(sys.stdin)]))'],{input:JSON.stringify(dates),encoding:'utf8'});
if(python.status!==0)throw Error(python.stderr);
const expected=JSON.parse(python.stdout),inline=[...fs.readFileSync('static/index.html','utf8').matchAll(/<script>([\s\S]*?)<\/script>/g)].at(-1)[1];
for(const zone of['UTC','America/New_York','Asia/Irkutsk']){
  process.env.TZ=zone;
  const context={Date,localStorage:{getItem(){return null;}},window:{addEventListener(){}}};vm.createContext(context);vm.runInContext(inline,context);
  for(let index=0;index<dates.length;index++){
    const [year,month,day,hour]=dates[index];context.target=new Date(year,month-1,day,hour);
    assert.equal(vm.runInContext('getWeekNum(target)',context),expected[index].week_number,`${zone} ${dates[index]}`);
    assert.equal(vm.runInContext('getReferenceDate(target).getDay()',context),1,'reference must be a Monday');
  }
}
console.log('Python/JS week parity: 429 boundary dates in three device timezones OK');
