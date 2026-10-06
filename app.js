const http = require('http');
const fs = require('fs');
const fsp = fs.promises;
const path = require('path');
const os = require('os');
const { spawn } = require('child_process');
const { URL } = require('url');

const PORT = Number(process.env.TODAY_LENS_PORT || 17891);
const ROOT = __dirname;
const DATA = path.join(process.env.LOCALAPPDATA || os.homedir(), 'Quicker', '今日脉络');
const PUBLIC = path.join(ROOT, 'public');
const jobs = new Map();
const extGroups = {
  document: new Set(['.doc','.docx','.wps','.txt','.md','.rtf','.odt']),
  sheet: new Set(['.xls','.xlsx','.csv','.et','.ods']),
  slide: new Set(['.ppt','.pptx','.dps','.odp']),
  pdf: new Set(['.pdf']), code: new Set(['.js','.ts','.tsx','.jsx','.py','.cs','.java','.go','.rs','.html','.css','.scss','.json','.xml','.yaml','.yml','.sql']),
  image: new Set(['.png','.jpg','.jpeg','.webp','.gif','.svg','.psd','.ai','.fig']),
  archive: new Set(['.zip','.7z','.rar','.tar','.gz']), installer: new Set(['.exe','.msi','.msix','.appx'])
};
const hardSkips = new Set(['$Recycle.Bin','System Volume Information','WinSxS','node_modules','.git','WindowsApps','Packages','Temp','Cache','Caches','Code Cache','GPUCache']);

async function ensureData(){ await fsp.mkdir(path.join(DATA,'logs'),{recursive:true}); }
function dayKey(d=new Date()){ return d.toISOString().slice(0,10); }
function json(res, code, value){ const body=JSON.stringify(value); res.writeHead(code,{'Content-Type':'application/json; charset=utf-8','Cache-Control':'no-store'}); res.end(body); }
async function readJson(file, fallback){ try{return JSON.parse(await fsp.readFile(file,'utf8'));}catch{return fallback;} }
async function saveJson(file,value){ await fsp.mkdir(path.dirname(file),{recursive:true}); await fsp.writeFile(file,JSON.stringify(value,null,2),'utf8'); }
function classify(file){ const e=path.extname(file).toLowerCase(); for(const [k,s] of Object.entries(extGroups)) if(s.has(e)) return k; return 'other'; }
function friendlyType(t){ return ({document:'文档',sheet:'表格',slide:'演示',pdf:'PDF',code:'代码',image:'图片',archive:'压缩包',installer:'安装包',other:'其他'})[t]; }
function rootsFrom(cfg){ return (cfg.drives||['C:','D:','E:']).filter(x=>fs.existsSync(x+'\\')).map(x=>x+'\\'); }
function shouldSkipDir(name, full, cfg){ if(hardSkips.has(name)) return true; const low=full.toLowerCase(); return (cfg.excludes||[]).some(x=>low.startsWith(String(x).toLowerCase())); }
function clusterKey(item){
  const base=path.basename(item.path,path.extname(item.path)).replace(/(?:副本|copy|最终|最新版|final|v?\d+(?:\.\d+)*|\(\d+\)|\[\d+\]|[-_ ]?\d{8,14})/ig,'').trim();
  if(item.type==='installer') return '安装软件';
  const parent=path.basename(path.dirname(item.path));
  return (base.length>3?base:parent).slice(0,42) || friendlyType(item.type);
}
function summarize(items){
  const groups=new Map();
  for(const item of items){ const k=clusterKey(item); if(!groups.has(k)) groups.set(k,[]); groups.get(k).push(item); }
  return [...groups.entries()].map(([title,files])=>{
    const types=[...new Set(files.map(x=>friendlyType(x.type)))];
    const verbs=files.some(x=>x.createdToday)?'新建并处理':'查看或修改';
    const text=title==='安装软件' ? `安装或更新了 ${files.length===1?path.basename(files[0].path):files.length+' 个相关组件'}。` : `${verbs}了“${title}”相关${types.join('、')}（${files.length} 个文件）。`;
    return {id:Buffer.from(title).toString('base64url'),title,text,count:files.length,files:files.slice(0,20),confidence:Math.min(.96,.58+files.length*.05)};
  }).sort((a,b)=>b.count-a.count).slice(0,30);
}
async function scan(job,cfg){
  const start=new Date(cfg.date+'T00:00:00'); const end=new Date(start); end.setDate(end.getDate()+1);
  const items=[]; const queue=rootsFrom(cfg); const max=Number(cfg.maxFiles||15000); let dirs=0, checked=0, truncated=false;
  job.status='running'; job.startedAt=Date.now(); job.roots=queue.slice();
  while(queue.length && items.length<max && !job.cancelled){
    const dir=queue.shift(); dirs++;
    let ents; try{ ents=await fsp.readdir(dir,{withFileTypes:true}); }catch{continue;}
    for(const e of ents){
      const full=path.join(dir,e.name); checked++;
      if(e.isDirectory()){ if(!shouldSkipDir(e.name,full,cfg)) queue.push(full); continue; }
      if(!e.isFile()) continue;
      let s; try{s=await fsp.stat(full);}catch{continue;}
      if(s.mtime>=start && s.mtime<end){ const type=classify(full); if((cfg.types||[]).length && !cfg.types.includes(type)) continue; items.push({path:full,name:e.name,type,size:s.size,modified:s.mtime.toISOString(),createdToday:s.birthtime>=start&&s.birthtime<end}); }
      if(items.length>=max){truncated=true;break;}
    }
    if(dirs%30===0){ job.progress={dirs,checked,found:items.length,current:dir,queued:queue.length}; await new Promise(r=>setImmediate(r)); }
  }
  const activities=summarize(items);
  const result={date:cfg.date,createdAt:new Date().toISOString(),roots:job.roots,stats:{files:items.length,activities:activities.length,dirs,checked,truncated},activities,items};
  await saveJson(path.join(DATA,'logs',cfg.date+'.json'),result);
  job.status=job.cancelled?'cancelled':'done'; job.progress={dirs,checked,found:items.length,current:'',queued:0}; job.result=result; job.finishedAt=Date.now();
}
function safePublic(file){ const full=path.normalize(path.join(PUBLIC,file==='/'?'index.html':file)); return full.startsWith(PUBLIC)?full:null; }
async function callAI(cfg, report){
  if(!cfg.endpoint || !cfg.model) throw new Error('请先填写 API 地址和模型');
  const endpoint=cfg.endpoint.replace(/\/$/,'')+(cfg.endpoint.endsWith('/chat/completions')?'':'/chat/completions');
  const evidence=report.activities.map((a,i)=>`${i+1}. ${a.text}\n证据：${a.files.map(f=>path.basename(f.path)).join('、')}`).join('\n');
  const prompt=`你是严谨的工作回顾助手。只依据证据归纳，不把“打开/修改”写成“已完成”。把同一软件安装产生的多个组件合成一件事，把同一项目的文件合成一件事。输出 JSON：{summary:string, highlights:string[], activities:[{title,description,evidenceCount}], risks:string[]}。\n日期：${report.date}\n${evidence}`;
  const body={model:cfg.model,temperature:.2,response_format:{type:'json_object'},messages:[{role:'system',content:'只返回有效 JSON，不泄露或猜测用户隐私。'},{role:'user',content:prompt}]};
  const resp=await fetch(endpoint,{method:'POST',headers:{'content-type':'application/json','authorization':`Bearer ${cfg.apiKey||''}`},body:JSON.stringify(body)});
  if(!resp.ok) throw new Error(`AI 请求失败：${resp.status} ${await resp.text()}`);
  const data=await resp.json(); const text=data.choices?.[0]?.message?.content||''; return JSON.parse(text.replace(/^```json\s*|\s*```$/g,''));
}
async function api(req,res,u){
  const parts=u.pathname.split('/').filter(Boolean); const method=req.method;
  const body=await new Promise((resolve,reject)=>{let x='';req.on('data',d=>{x+=d;if(x.length>2e6)reject(new Error('请求过大'));});req.on('end',()=>{try{resolve(x?JSON.parse(x):{});}catch(e){reject(e);}});});
  if(u.pathname==='/api/config'&&method==='GET') return json(res,200,await readJson(path.join(DATA,'config.json'),{theme:'auto',drives:['C:','D:','E:'],types:Object.keys(extGroups),excludes:[],maxFiles:15000,ai:{endpoint:'https://api.openai.com/v1',model:'gpt-5-mini',apiKey:''}}));
  if(u.pathname==='/api/config'&&method==='POST'){ await saveJson(path.join(DATA,'config.json'),body); return json(res,200,{ok:true}); }
  if(u.pathname==='/api/scan'&&method==='POST'){ const id=Date.now().toString(36); const job={id,status:'queued',progress:{dirs:0,checked:0,found:0}}; jobs.set(id,job); scan(job,body).catch(e=>{job.status='error';job.error=e.message}); return json(res,202,{id}); }
  if(parts[1]==='jobs'&&method==='GET') return json(res,200,jobs.get(parts[2])||{status:'missing'});
  if(parts[1]==='report'&&method==='GET') return json(res,200,await readJson(path.join(DATA,'logs',(parts[2]||dayKey())+'.json'),null));
  if(u.pathname==='/api/dates'&&method==='GET'){ const files=await fsp.readdir(path.join(DATA,'logs')).catch(()=>[]); return json(res,200,files.filter(x=>x.endsWith('.json')).map(x=>x.slice(0,-5)).sort().reverse()); }
  if(u.pathname==='/api/ai'&&method==='POST'){ const report=await readJson(path.join(DATA,'logs',body.date+'.json'),null); if(!report)return json(res,404,{error:'没有该日数据'}); const result=await callAI(body.ai,report); report.ai=result; await saveJson(path.join(DATA,'logs',body.date+'.json'),report); return json(res,200,result); }
  if(u.pathname==='/api/open'&&method==='POST'){ spawn('explorer.exe',[body.path],{detached:true,stdio:'ignore'}).unref(); return json(res,200,{ok:true}); }
  if(u.pathname==='/api/reveal'&&method==='POST'){ spawn('explorer.exe',['/select,',body.path],{detached:true,stdio:'ignore'}).unref(); return json(res,200,{ok:true}); }
  json(res,404,{error:'Not found'});
}
async function handler(req,res){ try{await ensureData(); const u=new URL(req.url,`http://${req.headers.host}`); if(u.pathname.startsWith('/api/'))return await api(req,res,u); const file=safePublic(decodeURIComponent(u.pathname)); if(!file||!fs.existsSync(file)){res.writeHead(404);return res.end('Not found');} const ext=path.extname(file); const types={'.html':'text/html; charset=utf-8','.css':'text/css; charset=utf-8','.js':'text/javascript; charset=utf-8','.svg':'image/svg+xml'};res.writeHead(200,{'Content-Type':types[ext]||'application/octet-stream'});fs.createReadStream(file).pipe(res);}catch(e){json(res,500,{error:e.message});} }
ensureData().then(()=>http.createServer(handler).listen(PORT,'127.0.0.1',()=>console.log(`今日脉络: http://127.0.0.1:${PORT}`)));
