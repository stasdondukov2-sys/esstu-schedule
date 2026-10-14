const fs = require('fs'), vm = require('vm'), assert = require('assert');
const html = fs.readFileSync('static/index.html', 'utf8');
const scripts = [...html.matchAll(/<script>([\s\S]*?)<\/script>/g)];
const elements = new Map();
const element = id => { if (!elements.has(id)) elements.set(id, {value:'',innerHTML:'',classList:{toggle(){},add(){},remove(){}}}); return elements.get(id); };
const ctx = {localStorage:{getItem(){return null},setItem(){}},window:{addEventListener(){}}, document:{getElementById:element},
  console, alert:message=>{ctx.alertMessage=message}, URLSearchParams, URL, setInterval(){}, clearInterval(){}};
vm.createContext(ctx);vm.runInContext(scripts.at(-1)[1], ctx);
vm.runInContext(fs.readFileSync('static/modern.js','utf8'), vm.createContext({...ctx, document:{...ctx.document,addEventListener(){}}}));
ctx.escapeHTML = value => String(value || '');
ctx.sample = {teacher_key:'семенов а.в.',caf_id:'Caf5',profile:{full_name:'Семёнов Алексей',department:'Физика'}, weeks:{1:{monday:{pairs:[{number:1,start:'09:00',end:'10:35',lessons:[{subject:'Квантовая механика',room:'8305'}]}]}}}};
for(const term of ['Семенов','семёнов','КВАНТОВАЯ','8305','Корпус 8']) {
  ctx.query=term;assert(vm.runInContext('teacherMatches(sample,query)',ctx),term);
}
assert(!vm.runInContext("teacherMatches(sample,'','Caf9')",ctx));
vm.runInContext('allTeachersDirectory=[sample]',ctx);
(async()=>{
  await vm.runInContext("loadTeacherSchedule('несуществующий','')",ctx);
  assert(ctx.alertMessage);assert.equal(vm.runInContext('currentSchedule',ctx),null);
  const data=JSON.parse(fs.readFileSync('dist/api/teachers/all/bakalavriat.json','utf8'));
  assert(data.count>0);ctx.directory=data.teachers;
  assert(vm.runInContext("directory.some(t=>teacherMatches(t,'дарибазарон'))",ctx));
  console.log(`Search checks OK; ${data.count} teachers from saved schedules`);
})().catch(error=>{console.error(error);process.exitCode=1});
