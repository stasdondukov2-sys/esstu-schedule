const fs=require('fs'),vm=require('vm'),assert=require('assert');
const inline=[...fs.readFileSync('static/index.html','utf8').matchAll(/<script>([\s\S]*?)<\/script>/g)];
const context={console,Date,Intl,URL,URLSearchParams,localStorage:{getItem(){return null;}},document:{addEventListener(){}},window:{addEventListener(){}},navigator:{onLine:true}};
vm.createContext(context);
for(const script of inline)new vm.Script(script[1]);
vm.runInContext(inline.at(-1)[1],context);
for(const file of ['modern.js','experience.js','simple-ui.js','study-tools.js'])vm.runInContext(fs.readFileSync('static/'+file,'utf8'),context);
const run=code=>vm.runInContext(code,context);
for(const date of ['2026-10-15T12:00:00','2026-01-01T12:00:00','2026-12-31T12:00:00','2026-10-18T12:00:00']){
  context.now=new Date(date);
  const current=run('getWeekNum(now)');context.week=current;
  assert.equal(run('getWeekRangeDates(week,now).monday.date.getDay()'),1);
  assert.equal(run('getWeekNum(getWeekRangeDates(week,now).monday.date)'),current);
  context.week=3-current;
  assert.equal(run('getWeekNum(getWeekRangeDates(week,now).monday.date)'),3-current);
  assert.equal(run('Object.values(getWeekRangeDates(week,now)).filter(d=>d.isToday).length'),0);
}
for(const room of ['0410','15-572','8305','0324 и/д']){
  context.room=room;assert(!run('decodeEsstuRoom(room).location.includes("этаж")'));
}
assert.equal(run('decodeEsstuRoom("04").building'),null);
assert.equal(run('decodeEsstuRoom("спорт").building'),null);
assert.equal(run('decodeEsstuRoom("0410").building'),'Корпус 4');
assert.equal(run('singleBuilding({lessons:[{room:"0410"},{room:"0422"}]})'),'Корпус 4');
assert.equal(run('singleBuilding({lessons:[{room:"0410"},{room:"8305"}]})'),null);
assert.equal(run('singleBuilding({lessons:[{room:"0410"},{}]})'),null);
context.now=new Date('2026-10-12T09:30:00');context.week=run('getWeekNum(now)');
context.schedule={weeks:{[context.week]:{monday:{pairs:[{number:1,start:'09:00',end:'10:35',lessons:[{subject:'A'},{subject:'B'}]},{number:2,start:'10:45',end:'12:20',lessons:[{subject:'C'}]}]}}}};
assert.equal(run('heroState(schedule,now).pair.lessons.length'),2);
assert.equal(run('heroState(schedule,now).remaining'),65);
for(const [time,kind] of [['08:59','next'],['09:00','current'],['10:35','next'],['10:45','current'],['12:20','finished']]){
  context.now=new Date('2026-10-12T'+time+':00');assert.equal(run('heroState(schedule,now).kind'),kind);
}
context.now=new Date('2026-10-18T09:30:00');assert.equal(run('heroState(schedule,now).kind'),'empty');
assert.equal(run('dayDateMeta({session_date:"25.12"},"monday",{}).shortLabel'),'25.12');
console.log('Calendar boundaries, lesson transitions, parallel lessons and conservative room decoding OK');

assert.equal(run('formatBreak(40)'), 'Перерыв 40 мин');
assert.equal(run('formatBreak(80)'), 'Окно 1 ч 20 мин');
assert.equal(run('formatBreak(120)'), 'Окно 2 ч');
assert.equal(run('durationText(868)'),'14 ч 28 мин');
for(const [n,word] of [[0,'пар'],[1,'пара'],[2,'пары'],[3,'пары'],[4,'пары'],[5,'пар'],[11,'пар'],[21,'пара']])assert.equal(run(`pairWord(${n})`),word);
context.onlinePairs=[{number:5,start:'16:25',end:'18:00',lessons:[{subject:'Основы проектной деятельности (онлайн-курс)',room:'онлайн',teacher:'Иванов И.И.'}]},{number:6,start:'18:05',end:'19:40',lessons:[{subject:'Основы проектной деятельности (онлайн-курс)',room:'онлайн',teacher:'Иванов И.И.'}]}];
const original=JSON.stringify(context.onlinePairs);
assert.equal(run('groupOnlinePairs(onlinePairs).length'),1);assert.equal(run('groupOnlinePairs(onlinePairs)[0].end'),1);assert.equal(JSON.stringify(context.onlinePairs),original);
assert.equal(run('displaySubject(onlinePairs[0].lessons[0])'),'Основы проектной деятельности');
for(const changes of [{teacher:'Другой П.П.'},{room:'0410'},{tag:'другая подгруппа'},{source_file:'other.htm'},{needs_review:true},{parse_warning:'Сверьте'}]){
 context.changed=structuredClone(context.onlinePairs);Object.assign(context.changed[1].lessons[0],changes);assert.equal(run('groupOnlinePairs(changed).length'),2);
}
context.changed=structuredClone(context.onlinePairs);context.changed.forEach(pair=>{pair.lessons[0].room='0410';});assert.equal(run('groupOnlinePairs(changed).length'),2);
console.log('Russian counts, hours, conservative online merging and intact source lessons OK');
