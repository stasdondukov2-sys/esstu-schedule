const fs=require('fs'),assert=require('assert');
const {yaml}=require('playwright-core/lib/utilsBundle');
const workflows={};
for(const name of fs.readdirSync('.github/workflows').filter(name=>name.endsWith('.yml'))){
  const document=yaml.parseDocument(fs.readFileSync('.github/workflows/'+name,'utf8'));
  assert.deepEqual(document.errors,[],name);
  const workflow=document.toJS();workflows[name]=workflow;
  for(const [jobName,job] of Object.entries(workflow.jobs)){
    if(job.uses)continue; // Reusable workflow owns its job timeouts.
    assert.equal(job['runs-on'],'ubuntu-24.04',`${name}/${jobName}`);
    assert(job['timeout-minutes']>0 && job['timeout-minutes']<=20,`${name}/${jobName}`);
    for(const step of job.steps || [])if(step.uses?.startsWith('actions/'))assert(/@[a-f0-9]{40}$/.test(step.uses),step.uses);
  }
}
const ci=workflows['ci.yml'].jobs.check.steps;
const tests=ci.findIndex(step=>step.name?.includes('regressions on frozen data'));
assert(tests<ci.findIndex(step=>step.name==='Restore durable validated data'));
assert(tests<ci.findIndex(step=>step.name==='Synchronize sources'));
assert(ci.find(step=>step.name?.includes('smoke-check')).run.includes('scripts.smoke_site'));
const cache=ci.find(step=>step.name==='Cache Playwright browsers');assert(cache.with.key.includes('package-lock.json'));
assert(workflows['sync.yml'].on.schedule.some(entry=>entry.cron==='*/30 0-9 * * 1-6'));
assert(workflows['sync.yml'].on.schedule.some(entry=>entry.cron==='0 10 * * 1-6'));
assert(workflows['freshness.yml'].on.schedule.length>0);
assert(workflows['freshness.yml'].on.workflow_run.types.includes('completed'));
assert(workflows['freshness.yml'].jobs.freshness.steps[0].with.ref==='main');
const dependabot=yaml.parse(fs.readFileSync('.github/dependabot.yml','utf8'));
assert(dependabot.updates.some(update=>update['package-ecosystem']==='github-actions'));
assert(dependabot.updates.some(update=>update['package-ecosystem']==='npm'));
assert(ci.find(step=>step.name?.includes('smoke-check')).run.includes('scripts.publication'));
assert.deepEqual(workflows['ci.yml'].on.push.branches,['main']);
assert.equal(workflows['ci.yml'].jobs.check.permissions.contents,'read');
const persist=workflows['ci.yml'].jobs['persist-data'];
assert.deepEqual(persist.needs,['check','deploy']);
assert(persist.if.includes("needs.deploy.result == 'success'"));
assert.equal(persist.permissions.contents,'write');
assert(!ci.some(step=>step.run?.includes('data_branch save')||step.run?.includes('data_branch checkpoint')));
assert(ci.find(step=>step.name?.includes('Contract regressions')).env.ESSTU_CONTRACT_TESTS==='1');
assert(workflows['ci.yml'].jobs.deploy.if.includes('inputs.rehearsal != true'));
console.log('Workflows: valid YAML, SHA pins, timeouts, frozen-before-live order, durable data restore, browser cache and freshness triggers OK');
