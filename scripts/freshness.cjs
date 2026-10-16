const TITLE='Расписание: выгрузка устарела';
function freshnessProblem(status,now=Date.now()){
  const issues=[];
  for(const [key,label] of [['generated_at','Сборка'],['source_checked_at_latest','Проверка источников']]){
    const stamp=Date.parse(status?.[key]);
    if(!Number.isFinite(stamp))issues.push(`${label}: дата неизвестна`);
    else if(stamp>now+300000)issues.push(`${label}: дата в будущем`);
    else if(now-stamp>12*3600000)issues.push(`${label}: более 12 часов назад (${new Date(stamp).toISOString()})`);
  }
  return issues.join('\n');
}
async function monitor({github,context,fetchImpl=fetch,now=Date.now()}){
  const {owner,repo}=context.repo;
  const url=`https://${owner}.github.io/${repo}/api/status.json`;
  let problem;
  try{
    const response=await fetchImpl(`${url}?freshness=${now}`,{cache:'no-store',signal:AbortSignal.timeout(15000)});
    if(!response.ok)throw Error(`HTTP ${response.status}`);
    problem=freshnessProblem(await response.json(),now);
  }catch(error){problem=`Не удалось проверить опубликованный status.json: ${error.message}`;}
  const issues=await github.paginate(github.rest.issues.listForRepo,{owner,repo,state:'open',creator:'github-actions[bot]'});
  const existing=issues.find(issue=>!issue.pull_request && issue.title===TITLE);
  if(problem){
    const body=`Опубликованные данные требуют проверки.\n\n${problem}\n\n[Статус сайта](${url}) · [Проверка](https://github.com/${owner}/${repo}/actions/runs/${context.runId}).`;
    if(existing)await github.rest.issues.update({owner,repo,issue_number:existing.number,body});
    else await github.rest.issues.create({owner,repo,title:TITLE,body});
  }else if(existing)await github.rest.issues.update({owner,repo,issue_number:existing.number,state:'closed',body:`Свежесть опубликованной выгрузки восстановлена. [Статус сайта](${url}).`});
  return problem;
}
module.exports={freshnessProblem,monitor};
