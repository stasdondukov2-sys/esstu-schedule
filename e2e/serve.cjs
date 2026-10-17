const http=require('http'),fs=require('fs'),path=require('path');
const root=path.resolve(process.env.ESSTU_E2E_SITE||'dist'),prefix='/esstu-schedule/';
const types={'.html':'text/html; charset=utf-8','.js':'text/javascript','.css':'text/css','.json':'application/json','.svg':'image/svg+xml','.png':'image/png'};
http.createServer((request,response)=>{
  const url=new URL(request.url,'http://localhost');
  if(!url.pathname.startsWith(prefix)){response.writeHead(404);return response.end();}
  let name;
  try{name=decodeURIComponent(url.pathname.slice(prefix.length));}catch{response.writeHead(400);return response.end();}
  const file=path.resolve(root,name||'index.html');
  if(!file.startsWith(root+path.sep)){response.writeHead(403);return response.end();}
  fs.readFile(file,(error,body)=>{
    response.writeHead(error?404:200,{'Content-Type':types[path.extname(file)]||'application/octet-stream','Cache-Control':'no-cache'});
    response.end(error?'Not found':body);
  });
}).listen(8768,'127.0.0.1');
