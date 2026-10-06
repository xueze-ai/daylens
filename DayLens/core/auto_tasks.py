import time,threading,requests,re
from datetime import datetime
from core.aggregator import aggregate,fallback_summary
from core.focus import analyze
from ai.client import generate

def push_serverchan(key,title,desp,short=''):
    desp=style_report(desp,title)
    r=requests.post(f'https://sctapi.ftqq.com/{key}.send',data={'title':title[:32],'desp':desp,'short':short[:64],'noip':'1'},timeout=15);r.raise_for_status();data=r.json()
    if data.get('code')!=0:raise RuntimeError(str(data));return data
def style_report(text,title='DayLens 日报'):
    lines=[]
    for raw in text.replace('\r','').split('\n'):
        line=raw.strip()
        if not line:continue
        if line.startswith(('#','-','*')) or re.match(r'^\d+[.、)]',line):lines.append(line)
        else:lines.append(line)
    return f"# {title}\n\n> 由 DayLens 自动生成\n\n"+'\n\n'.join(lines)+"\n\n---\n\n*DayLens · 每日镜*"
class AutoTasks:
    def __init__(self,repo,get_config,on_notice):self.repo=repo;self.get_config=get_config;self.on_notice=on_notice;self.stop_event=threading.Event();self.thread=None
    def start(self):self.stop_event.clear();self.thread=threading.Thread(target=self._run,daemon=True);self.thread.start()
    def stop(self):self.stop_event.set()
    def _run(self):
        while not self.stop_event.wait(30):
            c=self.get_config();now=datetime.now();day=now.strftime('%Y-%m-%d')
            if c.get('auto_summary') and now.strftime('%H:%M')==c.get('auto_summary_time','22:00') and not self.repo.daily_report(day):
                try:
                    data=aggregate(self.repo.file_events(day),self.repo.app_usage(day),self.repo.install_events(day));data['browser']=self.repo.browser_today(day);data['focus']=analyze(self.repo.samples(day));text=generate(c,day,data) if ((c['ai_mode']=='ollama' and c.get('ollama_model')) or c.get('api_key')) else fallback_summary(data);one=re.sub(r'[#*]','',text.splitlines()[2] if len(text.splitlines())>2 else text[:80]);self.repo.save_daily_report(day,text,one,0)
                    if c.get('serverchan_enabled') and c.get('serverchan_key'):
                        push_serverchan(c['serverchan_key'],f'DayLens · {day} 日报',text,one);self.repo.save_daily_report(day,text,one,1)
                    self.on_notice('今日总结已生成'+('并推送' if c.get('serverchan_enabled') else ''))
                except Exception as e:self.on_notice('自动日报失败：'+str(e))
