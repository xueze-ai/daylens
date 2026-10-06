import json,requests,re,difflib

SYSTEM="""你是个人电脑活动分析助手。只依据结构化证据写中文复盘，不罗列原始路径，不把打开软件写成已完成任务。最多8条，每条小于40个字，用主谓宾短句。禁止使用：依托、伴随、呈现出、场景、流转、闭环、赋能、深耕、旨在、聚焦于。好例子：“微信收到9个文件，多为图片。”如果 active_seconds < 1800，必须输出“今日电脑使用时间过短”，不要下全天判断。只有 active_seconds > 14400 才允许使用“全天”。最后给出“今日一句话”。只输出Markdown。"""
def checked(r):
    if r.status_code==401:raise RuntimeError('AI 鉴权失败（401）：请检查 API Key 是否有效、是否属于当前服务，以及 API 地址是否正确。')
    if r.status_code==403:raise RuntimeError('AI 无访问权限（403）：当前 Key 没有调用该模型的权限。')
    if r.status_code==404:raise RuntimeError('AI 地址或模型不存在（404）：请检查 Base URL 和模型名称。')
    r.raise_for_status();return r
def prompt(day,data):
    apps=[{'software':x['display_name'],'seconds':round(x['seconds']),'sessions':x['sessions'],'sample_title':x.get('window_title','')[:80]} for x in data['apps'][:30]]
    clusters=[{k:x[k] for k in ('type','title','description','file_count','first_seen','last_seen')} for x in data['clusters'][:60]]
    browser=data.get('browser',[])[:10];focus=data.get('focus',{});timing={k:focus.get(k,0) for k in ('total_span_seconds','active_seconds','idle_seconds')};notes=[{'time':x.get('ts'),'text':x.get('text','')[:500]} for x in data.get('notes',[])[:20]]
    return f"日期：{day}\n时间上下文：{json.dumps(timing,ensure_ascii=False)}\n软件使用：{json.dumps(apps,ensure_ascii=False)}\n活动聚类：{json.dumps(clusters,ensure_ascii=False)}\n网页浏览Top10：{json.dumps(browser,ensure_ascii=False)}\n用户速记：{json.dumps(notes,ensure_ascii=False)}\n专注度：{json.dumps(focus,ensure_ascii=False,default=str)}"
def clean_summary(text):
    banned=['依托','伴随','呈现出','场景','流转','闭环','赋能','深耕','旨在','聚焦于'];lines=[]
    for line in text.splitlines():
        for word in banned:line=line.replace(word,'')
        plain=re.sub(r'^[\s#*\-\d.、]+','',line).strip()
        if plain and any(difflib.SequenceMatcher(None,plain,re.sub(r'^[\s#*\-\d.、]+','',x).strip()).ratio()>.85 for x in lines if x.strip()):continue
        if len(plain)>40:
            prefix=line[:max(0,line.find(plain))];line=prefix+plain[:39]+'…'
        lines.append(line)
    return '\n'.join(lines)
def enforce_timing(text,data):
    active=data.get('focus',{}).get('active_seconds',0);text=clean_summary(text)
    if active<1800 and '今日电脑使用时间过短' not in text:text='> 今日电脑使用时间过短，以下仅代表已记录时段。\n\n'+text
    if active<=14400:text=text.replace('全天','已记录时段')
    return text
def generate(config,day,data):
    p=prompt(day,data)
    if config['ai_mode']=='ollama':
        url=config['ollama_url'].rstrip('/')+'/api/chat';body={'model':config['ollama_model'],'stream':False,'messages':[{'role':'system','content':SYSTEM},{'role':'user','content':p}]};r=checked(requests.post(url,json=body,timeout=180));return enforce_timing(r.json()['message']['content'],data)
    url=config['base_url'].rstrip('/')
    if not url.endswith('/chat/completions'):url+='/chat/completions'
    r=checked(requests.post(url,headers={'Authorization':'Bearer '+config['api_key'],'Content-Type':'application/json'},json={'model':config['model'],'temperature':0.2,'messages':[{'role':'system','content':SYSTEM},{'role':'user','content':p}]},timeout=180));return enforce_timing(r.json()['choices'][0]['message']['content'],data)
def generate_snapshot(config,base_time,compare_time,diff):
    from collections import defaultdict
    from pathlib import Path
    groups=defaultdict(lambda:{'count':0,'size':0,'samples':[]})
    for typ in ('added','modified','deleted'):
        for x in diff[typ]:
            p=Path(x['path']);root=str(Path(*p.parts[:min(4,len(p.parts)-1)]));g=groups[(typ,root)];g['count']+=1;g['size']+=x.get('size',0)
            if len(g['samples'])<5:g['samples'].append(p.name)
    clusters=[{'action':k[0],'top_dir':k[1],**v} for k,v in sorted(groups.items(),key=lambda z:-z[1]['count'])[:30]]
    user=f"基准快照：{base_time}\n对比快照：{compare_time}\n差异摘要：{json.dumps(clusters,ensure_ascii=False)}"
    system="你是个人电脑活动分析助手。用中文解释两次快照之间用户可能做了什么。不要罗列原始路径。最多6条，识别安装软件、修改项目、集中处理办公文档和超过500MB的清理行为。最后给出这段时间的一句话总结。只输出Markdown。"
    if config['ai_mode']=='ollama':
        r=requests.post(config['ollama_url'].rstrip('/')+'/api/chat',json={'model':config['ollama_model'],'stream':False,'messages':[{'role':'system','content':system},{'role':'user','content':user}]},timeout=180);r.raise_for_status();return r.json()['message']['content']
    url=config['base_url'].rstrip('/');url=url if url.endswith('/chat/completions') else url+'/chat/completions';r=requests.post(url,headers={'Authorization':'Bearer '+config['api_key'],'Content-Type':'application/json'},json={'model':config['model'],'messages':[{'role':'system','content':system},{'role':'user','content':user}]},timeout=180);r.raise_for_status();return r.json()['choices'][0]['message']['content']
def summarize_document(config,name,text):
    system='请用中文分析文档的实际内容，不要只根据文件名猜测。输入中的“最后一页/末尾”是分析重点。请输出：文档用途、主要主题、末页/末段表达的结论、三个关键要点。证据不足时明确说明，不得编造。只输出 Markdown。';user=f'文件名（仅供识别）：{name}\n以下是从文档中实际提取的内容：\n{text[:30000]}'
    if config['ai_mode']=='ollama':
        r=requests.post(config['ollama_url'].rstrip('/')+'/api/chat',json={'model':config['ollama_model'],'stream':False,'messages':[{'role':'system','content':system},{'role':'user','content':user}]},timeout=180);r.raise_for_status();return r.json()['message']['content']
    url=config['base_url'].rstrip('/');url=url if url.endswith('/chat/completions') else url+'/chat/completions';r=requests.post(url,headers={'Authorization':'Bearer '+config['api_key'],'Content-Type':'application/json'},json={'model':config['model'],'messages':[{'role':'system','content':system},{'role':'user','content':user}]},timeout=180);r.raise_for_status();return r.json()['choices'][0]['message']['content']
