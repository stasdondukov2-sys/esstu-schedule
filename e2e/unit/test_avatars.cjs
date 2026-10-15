const fs=require('fs'),vm=require('vm'),assert=require('assert');
const html=fs.readFileSync('static/index.html','utf8'),inline=[...html.matchAll(/<script>([\s\S]*?)<\/script>/g)].at(-1)[1];
const elements=new Map(),context={console,URL,URLSearchParams,Date,Intl,localStorage:{getItem(){return null;}},window:{addEventListener(){}},document:{addEventListener(){},getElementById(id){if(!elements.has(id))elements.set(id,{value:'',innerHTML:'',classList:{contains(){return true;}}});return elements.get(id);}}};
vm.createContext(context);vm.runInContext(inline,context);vm.runInContext(fs.readFileSync('static/modern.js','utf8'),context);
const run=code=>vm.runInContext(code,context);
for(const photo of ['https://ui-avatars.com/api/?name=A','https://evil.invalid/p.png','//evil.invalid/p.png','javascript:alert(1)','data:image/svg+xml,<svg onload="x"/>','avatars/../x.png','avatars/p.png" onerror="evil()']){
  context.profile={photo,short_name:'Иванов И.И.'};
  assert(run('teacherAvatarURL(profile).startsWith("data:image/svg+xml;charset=utf-8,")'));
}
context.profile={photo:'avatars/teacher.webp',short_name:'Иванов И.И.'};
assert.equal(run('teacherAvatarURL(profile)'),'avatars/teacher.webp');
context.profile={photo:'https://evil.invalid/p.png" onerror="ATTACK()',short_name:'"><img src=x onerror="ATTACK()">',full_name:'"><script>ATTACK()</script>',degree:'<b>unsafe</b>',department:'<img src=x onerror=ATTACK()>'};
context.maliciousKey='bad" onclick=ATTACK()';
run('allTeachersDirectory=[{teacher_key:maliciousKey,caf_id:"Caf5",profile,weeks:{}}];renderTeacherModalContent()');
const rendered=elements.get('teacherModalContent').innerHTML;
assert(!rendered.includes('src="https://evil'));
assert(!rendered.includes('<script>ATTACK()'));
assert(!rendered.includes('<img src=x'));
assert(rendered.includes('chooseTeacherByIndex(0)'));
assert(!html.includes('/api/teacher/meta'));
assert(!html.includes('photoModal'));
assert(!fs.readFileSync('teachers_meta.json','utf8').includes('ui-avatars.com'));
console.log('Local avatars, legacy URL rejection, escaped metadata and read-only profile UI OK');
