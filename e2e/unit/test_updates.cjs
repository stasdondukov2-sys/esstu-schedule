const fs=require('fs'),vm=require('vm'),assert=require('assert');
async function setup(controlled=true){
 const events={},docEvents={},timers=[],intervals=[],button={disabled:false,textContent:''};let reloads=0,checks=0;
 const registration={waiting:null,addEventListener(){},update(){checks++;return Promise.resolve();}};
 const context={console:{...console,warn(){}},updateLiveHero(){},window:{},document:{visibilityState:'visible',addEventListener(n,fn){docEvents[n]=fn;},getElementById(){return {classList:{remove(){}},...button};}},navigator:{serviceWorker:{controller:controlled?{}:null,addEventListener(n,fn){events[n]=fn;},register:async(url,options)=>{assert.equal(options.updateViaCache,'none');return registration;}}},location:{reload(){reloads++;}},setTimeout(fn,ms){timers.push({fn,ms});return timers.length;},clearTimeout(){},setInterval(fn,ms){intervals.push({fn,ms});}};
 vm.createContext(context);vm.runInContext(fs.readFileSync('static/experience.js','utf8'),context);await vm.runInContext('initAppUpdates()',context);
 return {context,events,docEvents,timers,intervals,button,get reloads(){return reloads;},get checks(){return checks;},run(code){return vm.runInContext(code,context);}};
}
(async()=>{
 let app=await setup();app.events.controllerchange();app.events.controllerchange();assert.equal(app.reloads,1,'controlled peer reloads once without clicking');
 app=await setup(false);app.events.controllerchange();assert.equal(app.reloads,0,'first installation does not reload');app.events.controllerchange();assert.equal(app.reloads,1);
 app=await setup();assert.equal(app.intervals[0].ms,900000);app.context.document.visibilityState='hidden';app.intervals[0].fn();assert.equal(app.checks,0);app.context.document.visibilityState='visible';app.docEvents.visibilitychange();assert.equal(app.checks,1);
 app=await setup();let sent;app.context.worker={postMessage(value){sent=value;}};app.run('pendingWorker=worker');app.context.button=app.button;await app.run('applyAppUpdate({currentTarget:button})');assert(app.button.disabled);assert.equal(app.button.textContent,'Обновление…');assert.equal(sent.type,'SKIP_WAITING');assert.equal(app.timers[0].ms,4000);app.timers[0].fn();assert.equal(app.reloads,1);
 app=await setup();app.context.worker={postMessage(){throw Error('test delivery failure');}};app.run('pendingWorker=worker');await app.run('applyAppUpdate()');assert.equal(app.reloads,1);
 console.log('Worker peers, first installation, visible polling and update fallback OK');
})().catch(error=>{console.error(error);process.exitCode=1;});
