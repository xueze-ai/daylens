def analyze(samples):
    if not samples:return {'score':0,'switch_count':0,'avg_focus':0,'longest_focus':0,'longest_app':'','idle_seconds':0,'active_seconds':0,'total_span_seconds':0,'fragmentation':0}
    sessions=[];cur=None;idle_seconds=0
    for s in samples:
        if s['idle']:
            idle_seconds+=5;key='__idle__';name='空闲'
        else:key=s['process'];name=s['display_name']
        if not cur or cur[0]!=key:
            if cur:sessions.append(cur)
            cur=[key,name,s['ts'],s['ts']+5]
        else:cur[3]=s['ts']+5
    if cur:sessions.append(cur)
    # 同进程 30 秒内再次激活视为同一专注段；小于 3 秒的短段不进入统计。
    merged=[]
    for x in sessions:
        if x[3]-x[2]<3:continue
        previous=next((i for i in range(len(merged)-1,-1,-1) if merged[i][0]==x[0]),-1)
        if x[0]!='__idle__' and previous>=0 and x[2]-merged[previous][3]<=30:
            # A brief switch away and back is one continuous working segment.
            merged[previous][3]=x[3];del merged[previous+1:]
        else:merged.append(x)
    sessions=merged;active=[x for x in sessions if x[0]!='__idle__'];dur=[x[3]-x[2] for x in active];active_seconds=sum(dur);switches=max(0,len(active)-1);hours=max(active_seconds/3600,.01);frag=switches/hours;idle_ratio=idle_seconds/max(active_seconds+idle_seconds,1);score=max(0,round(100-min(60,frag*.8)-min(20,idle_ratio*100)))
    longest=max(active,key=lambda x:x[3]-x[2],default=['','',0,0])
    span=(samples[-1]['ts']-samples[0]['ts']+5) if samples else 0
    return {'score':score,'switch_count':switches,'avg_focus':sum(dur)/len(dur) if dur else 0,'longest_focus':longest[3]-longest[2],'longest_app':longest[1],'idle_seconds':idle_seconds,'active_seconds':active_seconds,'total_span_seconds':span,'fragmentation':frag,'sessions':sessions}
