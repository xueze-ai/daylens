import os,re
from pathlib import Path
from collections import defaultdict

DOC={'.doc','.docx','.wps','.rtf','.odt','.txt','.md','.pdf'}; CODE={'.py','.js','.ts','.tsx','.jsx','.cs','.java','.go','.rs','.cpp','.c','.h','.html','.css','.scss','.json','.xml','.yml','.yaml','.sql'}
MEDIA={'.png','.jpg','.jpeg','.webp','.gif','.svg','.psd','.ai','.mp4','.mov','.avi','.mp3','.wav'}; SHEET={'.xls','.xlsx','.csv','.et','.ods'}
def kind(path):
    e=Path(path).suffix.lower()
    if e in CODE:return '代码'
    if e in SHEET:return '表格'
    if e in DOC:return '文档'
    if e in MEDIA:return '图片/媒体'
    if e in {'.exe','.msi','.msix','.appx'}:return '安装包'
    if e in {'.zip','.rar','.7z','.tar','.gz'}:return '压缩包'
    return '其他文件'
def project_root(path):
    p=Path(path);parts=p.parts
    for marker in ('src','app','lib','pages','components','Documents','Desktop','Downloads'):
        if marker in parts:
            i=parts.index(marker);return str(Path(*parts[:max(i,1)+1]))
    return str(p.parent)
def label_from_path(p):
    name=Path(p).name or Path(p).parent.name
    return re.sub(r'[-_]+',' ',name).strip()[:48]
def aggregate(files,apps,installs):
    clusters=[];bucket=defaultdict(list)
    for e in files:
        if e['is_dir']:continue
        p=e['path'];low=p.lower()
        if '\\program files\\' in low or '\\appdata\\local\\programs\\' in low:
            parts=Path(p).parts;idx=next((i for i,x in enumerate(parts) if x.lower() in {'program files','program files (x86)','programs'}),len(parts)-2);root=str(Path(*parts[:min(idx+2,len(parts))]));bucket[('software',root)].append(e)
        elif '\\downloads\\' in low:bucket[('download',str(Path(p).parent))].append(e)
        else:bucket[('work',project_root(p),kind(p))].append(e)
    for key,rows in bucket.items():
        typ=key[0]
        # 同一路径可能同时被“首次基线”和实时监控捕获，先按路径保留最后状态，避免重复证据。
        rows=list({x['path']:x for x in rows}.values())
        created=sum(x['event_type']=='created' for x in rows);modified=sum(x['event_type'] in {'modified','baseline'} for x in rows);deleted=sum(x['event_type']=='deleted' for x in rows)
        first=min(x['ts'] for x in rows);last=max(x['ts'] for x in rows);root=key[1]
        if typ=='software':
            if len(rows)>=8:
                title=f"安装或更新了 {label_from_path(root)}";desc=f"该软件目录在 {int((last-first)/60)+1} 分钟内出现 {len(rows)} 次变更。"
            else:
                title=f"{label_from_path(root)} 软件目录有变化";desc=f"检测到 {len(rows)} 个相关文件变化，证据不足以判断为一次完整安装。"
        elif typ=='download':
            large=[x for x in rows if x['size']>=100*1024*1024];title=f"下载了 {len(rows)} 个文件";desc=(f"其中 {len(large)} 个超过 100 MB。" if large else "下载内容已归并显示。")
        else:
            k=key[2];label=label_from_path(root);verb='编写/修改' if k=='代码' else '处理'
            title=f"{verb}了“{label}”中的{k}";desc=f"涉及 {len(rows)} 条文件变化（新增 {created}、修改 {modified}、删除 {deleted}）。"
        clusters.append({'type':typ,'title':title,'description':desc,'path':root,'file_count':len(rows),'first_seen':first,'last_seen':last,'files':rows[:80]})
    seen_installs=set()
    for e in installs:
        dedupe=(e['name'].strip().lower(),e['action'])
        if dedupe in seen_installs:continue
        seen_installs.add(dedupe)
        action={'installed':'安装了','uninstalled':'卸载了','updated':'更新了'}.get(e['action'],e['action']);clusters.append({'type':'install','title':f"{action} {e['name']}",'description':'根据 Windows 已安装软件清单变化确认。','path':'','file_count':0,'first_seen':e['ts'],'last_seen':e['ts'],'files':[]})
    clusters.sort(key=lambda x:(x['type']!='install',-x['last_seen']))
    total=sum(a['seconds'] for a in apps)
    return {'apps':apps,'clusters':clusters,'total_active':total,'file_count':len(files),'app_count':len(apps)}
def fallback_summary(data):
    acts=[]
    for a in data['apps'][:5]:
        mins=round(a['seconds']/60);acts.append(f"**使用 {a['display_name']}**：前台活跃约 {mins} 分钟，共 {a['sessions']} 段。")
    acts += [f"**{c['title']}**：{c['description']}" for c in data['clusters'][:8-len(acts)]]
    if not acts:return "今天尚未积累足够的活动记录。DayLens 会从现在开始持续记录。"
    main=data['apps'][0]['display_name'] if data['apps'] else data['clusters'][0]['title']
    return "## 今日一句话\n\n今天的主要活动集中在 **%s**。\n\n## 主要活动\n\n%s"%(main,'\n\n'.join(f'{i+1}. {x}' for i,x in enumerate(acts)))
