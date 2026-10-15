const fs=require('fs'),vm=require('vm'),assert=require('assert');
const scripts=[...fs.readFileSync('static/index.html','utf8').matchAll(/<script>([\s\S]*?)<\/script>/g)];
const storage=new Map();
const context={console,localStorage:{getItem:key=>storage.get(key)||null,setItem:(key,val)=>storage.set(key,val)},
 document:{addEventListener(){}},window:{addEventListener(){}},navigator:{onLine:true},URL,URLSearchParams,setInterval(){},clearInterval(){},Intl,Date};
vm.createContext(context);vm.runInContext(scripts.at(-1)[1],context);
vm.runInContext(fs.readFileSync('static/modern.js','utf8'),context);
vm.runInContext(fs.readFileSync('static/experience.js','utf8'),context);
context.previous=[{week:'1',day:'monday',pair:1,start:'09:00',end:'10:35',subject:'Physics',room:'0410',teacher:'A',groups:'X',tag:'',type:'Lab'},
 {week:'1',day:'monday',pair:1,start:'09:00',end:'10:35',subject:'Math',room:'0420',teacher:'B',groups:'X',tag:'2',type:'Lab'}];
context.current=structuredClone(context.previous);context.current[1].room='0422';
assert.equal(vm.runInContext('compareSchedules(previous,current).length',context),1);
assert(vm.runInContext('compareSchedules(previous,current)[0].label.includes("0420 → 0422")',context));
context.current=structuredClone(context.previous).reverse();
assert.equal(vm.runInContext('compareSchedules(previous,current).length',context),0,'order is not a change');
context.current=[];assert.equal(vm.runInContext('compareSchedules(previous,current).filter(c=>c.kind==="removed").length',context),2);
context.current=structuredClone(context.previous);context.current[0].day='tuesday';
assert.equal(vm.runInContext('compareSchedules(previous,current).length',context),1,'detect a real move');
assert.equal(vm.runInContext('compareSchedules(null,current).length',context),0,'first load is not a change');
context.room={slots:{'1:monday:1':[{pair:1,start:'09:00',end:'10:35',subject:'Physics'}]}};
for(const [minutes,count]of[[540,1],[634,1],[635,0],[640,0]]){
 context.check={week:1,day:0,pair:null,minutes};assert.equal(vm.runInContext('roomOccupancy(room,check).busy.length',context),count);
}
context.check={week:1,day:6,pair:1};assert.equal(vm.runInContext('roomOccupancy(room,check).busy.length',context),0);
context.check={week:1,day:0,pair:1};assert.equal(vm.runInContext('roomOccupancy(room,check).busy.length',context),1);
console.log('Diff, first load, lesson order, moves, removals, breaks and Sunday checks OK');
