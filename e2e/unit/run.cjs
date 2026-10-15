const fs=require('fs'),path=require('path'),{spawnSync}=require('child_process');
for(const file of fs.readdirSync(__dirname).filter(file=>/^test_.*\.cjs$/.test(file))){
  const result=spawnSync(process.execPath,[path.join(__dirname,file)],{stdio:'inherit'});
  if(result.status!==0)process.exit(result.status||1);
}
