import os,sys,time,html,json,csv
from datetime import datetime
from pathlib import Path
from PySide6.QtCore import Qt,QThread,Signal,QTimer,QDate,QUrl,QPoint
from PySide6.QtGui import QDesktopServices,QIcon,QKeySequence,QShortcut
from PySide6.QtPrintSupport import QPrinter
from PySide6.QtWidgets import *
import markdown
from core.aggregator import aggregate,fallback_summary,kind
from core.snapshot import capture,compare
from ai.client import generate,generate_snapshot,summarize_document
from config.manager import save_config,set_autostart
from ui.settings_dialog import SettingsDialog
from ui.theme import LIGHT,DARK
from ui.timeline import TimelineWidget
from ui.widgets.date_picker import CustomDatePicker
from core.focus import analyze

def duration(s):
    s=int(s);h,s=divmod(s,3600);m=s//60
    return (f'{h} 小时 {m} 分钟' if h else f'{m} 分钟')
def focus_duration(seconds):
    seconds=max(0,int(seconds))
    if seconds<60:return f'{seconds} 秒'
    minutes=seconds//60
    if minutes<60:return f'{minutes} 分钟'
    return f'{minutes//60} 小时 {minutes%60} 分钟'
class Worker(QThread):
    done=Signal(object);failed=Signal(str);progress=Signal(str)
    def __init__(self,fn):super().__init__();self.fn=fn
    def run(self):
        try:self.done.emit(self.fn(self.progress.emit))
        except Exception as e:self.failed.emit(str(e))
class DatePickerDialog(QDialog):
    def __init__(self,date,parent=None):
        super().__init__(parent);self.setWindowTitle('选择日期');v=QVBoxLayout(self);v.addWidget(QLabel('请输入年月日'));row=QHBoxLayout();self.y=QLineEdit(str(date.year()));self.m=QLineEdit(str(date.month()));self.d=QLineEdit(str(date.day()))
        from PySide6.QtGui import QIntValidator
        self.y.setValidator(QIntValidator(2000,2100,self));self.m.setValidator(QIntValidator(1,12,self));self.d.setValidator(QIntValidator(1,31,self))
        for w,t in [(self.y,'年'),(self.m,'月'),(self.d,'日')]:w.setMaximumWidth(90);row.addWidget(w);row.addWidget(QLabel(t))
        v.addLayout(row);buttons=QDialogButtonBox(QDialogButtonBox.Ok|QDialogButtonBox.Cancel);buttons.accepted.connect(self.accept);buttons.rejected.connect(self.reject);v.addWidget(buttons)
    def value(self):return QDate(int(self.y.text()),int(self.m.text()),int(self.d.text()))
class MainWindow(QMainWindow):
    config_changed=Signal(dict)
    def __init__(self,repo,config):
        super().__init__();self.repo=repo;self.config=config;self.data={};self.tasks={};self.refresh_worker=None;self.history_worker=None;self.refresh_pending=False;self.refresh_cache={}
        self.setWindowTitle('DayLens 每日镜 V1.0.9');self.resize(1180,820);self.setMinimumSize(900,650);self.refresh_request_id=0;self.last_system_date=QDate.currentDate();self._build();self.apply_theme();self.refresh()
        self.timer=QTimer(self);self.timer.timeout.connect(self.periodic_tick);self.timer.start(30000)
        self.auto_ai_timer=QTimer(self);self.auto_ai_timer.timeout.connect(self.auto_ai_refresh);self.auto_ai_timer.start(1800000);QTimer.singleShot(120000,self.auto_ai_refresh)
    def start_task(self,key,worker):
        old=self.tasks.get(key)
        if old and old.isRunning():return False
        worker.setParent(self);self.tasks[key]=worker;worker.finished.connect(lambda k=key,w=worker:self.release_task(k,w));worker.start();return True
    def release_task(self,key,worker):
        if self.tasks.get(key) is worker:self.tasks.pop(key,None)
        worker.deleteLater()
    def shutdown_tasks(self):
        self.timer.stop();self.auto_ai_timer.stop()
        workers=list(self.tasks.values())+[x for x in (self.refresh_worker,self.history_worker) if x]
        for worker in workers:
            if worker and worker.isRunning():worker.requestInterruption();worker.wait()
    def _build(self):
        root=QWidget();self.setCentralWidget(root);v=QVBoxLayout(root);v.setContentsMargins(24,18,24,18);v.setSpacing(14)
        top=QHBoxLayout();brand=QVBoxLayout();title=QLabel('DayLens · 每日镜');title.setObjectName('title');sub=QLabel('把电脑活动翻译成今天真正做过的事');sub.setObjectName('muted');brand.addWidget(title);brand.addWidget(sub);top.addLayout(brand);top.addStretch()
        self.search_box=QLineEdit();self.search_box.setPlaceholderText('全局搜索  Ctrl+F');self.search_box.setMaximumWidth(190);self.search_box.returnPressed.connect(self.global_search);top.addWidget(self.search_box);note=QPushButton('＋ 速记');note.setToolTip('记录当前想法（Ctrl+Alt+N）');note.clicked.connect(self.quick_note);top.addWidget(note);export=QToolButton();export.setText('导出 ▾');export.setPopupMode(QToolButton.InstantPopup);menu=QMenu(export)
        for label,ext in [('CSV','.csv'),('JSON','.json'),('Markdown','.md'),('PDF','.pdf')]:act=menu.addAction(label);act.triggered.connect(lambda _,e=ext:self.export_current(e))
        export.setMenu(menu);top.addWidget(export);self.current_date=QDate.currentDate();prev=QPushButton('←');prev.setToolTip('前一天');prev.clicked.connect(lambda:self.change_day(-1));top.addWidget(prev);self.date_btn=QPushButton();self.date_btn.setMinimumWidth(176);self.date_btn.clicked.connect(self.pick_date);self.update_date_text();top.addWidget(self.date_btn);nxt=QPushButton('→');nxt.setToolTip('后一天');nxt.clicked.connect(lambda:self.change_day(1));top.addWidget(nxt);refresh=QPushButton('⟳ 刷新');refresh.setToolTip('立即刷新软件时长、网页浏览和文件活动');refresh.clicked.connect(lambda:self.refresh(True));top.addWidget(refresh);self.theme_btn=QPushButton('◐');self.theme_btn.setToolTip('切换明亮/深色主题');self.theme_btn.setFixedSize(48,42);self.theme_btn.setStyleSheet('QPushButton{font-size:26px;border:0;background:transparent;padding:0}');self.theme_btn.clicked.connect(self.toggle_theme);top.addWidget(self.theme_btn);settings=QPushButton('设置');settings.clicked.connect(self.settings);top.addWidget(settings);snap=QPushButton('立即快照');snap.setObjectName('primary');snap.clicked.connect(self.take_snapshot);top.addWidget(snap);v.addLayout(top)
        QShortcut(QKeySequence('Ctrl+F'),self,activated=lambda:self.search_box.setFocus());QShortcut(QKeySequence('Ctrl+Alt+N'),self,activated=self.quick_note)
        try:
            from db.repository import DB_PATH
            if DB_PATH.exists() and DB_PATH.stat().st_size>1024**3:
                warn=QLabel(f'数据库已占用 {DB_PATH.stat().st_size/1024**3:.1f} GB。建议在设置中缩短数据保留天数。');warn.setStyleSheet('background:#FFF4D6;color:#7A5200;border:1px solid #F1D58A;border-radius:8px;padding:9px 12px');v.addWidget(warn)
        except OSError:pass
        self.tabs=QTabWidget();v.addWidget(self.tabs,1);self.tabs.addTab(self._today(),'今日');self.tabs.addTab(self._wechat(),'微信文件');self.tabs.addTab(self._snapshots(),'快照对比');self.tabs.addTab(self._history(),'每日记录');self.tabs.currentChanged.connect(self.on_tab_changed)
        self.statusBar().showMessage('后台监控运行中 · 软件时长从 DayLens 启动后开始累计')
    def card(self):f=QFrame();f.setObjectName('card');return f
    def _today(self):
        page=QWidget();v=QVBoxLayout(page);v.setContentsMargins(0,14,0,0);v.setSpacing(14)
        metrics=self.card();h=QHBoxLayout(metrics);self.metric_labels=[]
        for label in ['总活跃','使用软件','文件变化','AI 归纳事件数']:
            box=QVBoxLayout();a=QLabel(label);a.setObjectName('muted');b=QLabel('0');b.setObjectName('metric');box.addWidget(a);box.addWidget(b);h.addLayout(box);h.addStretch();self.metric_labels.append(b)
        v.addWidget(metrics)
        self.timeline=TimelineWidget();v.addWidget(self.timeline);timeline_hint=QLabel('滚轮缩放 · 按住左键左右拖动 · 悬停查看精确时段 · 双击恢复全天');timeline_hint.setObjectName('muted');v.addWidget(timeline_hint)
        focus=self.card();fh=QHBoxLayout(focus);self.focus_score=QLabel('数据积累中');self.focus_score.setObjectName('metric');fh.addWidget(self.focus_score);self.focus_bar=QProgressBar();self.focus_bar.setTextVisible(False);self.focus_bar.setRange(0,100);fh.addWidget(self.focus_bar,1);self.focus_detail=QLabel('持续使用后显示专注度指标');self.focus_detail.setObjectName('muted');fh.addWidget(self.focus_detail,2);v.addWidget(focus)
        head=QHBoxLayout();lab=QLabel('今日复盘');lab.setObjectName('section');head.addWidget(lab);head.addStretch();self.ai_btn=QPushButton('生成 AI 今日总结');self.ai_btn.setObjectName('primary');self.ai_btn.clicked.connect(self.run_ai);head.addWidget(self.ai_btn);v.addLayout(head)
        self.ai_status=QLabel('');self.ai_status.setObjectName('muted');head.addWidget(self.ai_status);self.ai_progress=QProgressBar();self.ai_progress.setRange(0,0);self.ai_progress.setTextVisible(False);self.ai_progress.setMaximumWidth(150);self.ai_progress.hide();head.addWidget(self.ai_progress);self.summary=QTextBrowser();self.summary.setOpenExternalLinks(False);self.summary.setMinimumHeight(240);v.addWidget(self.summary,2)
        splitter=QSplitter(Qt.Horizontal);left=self.card();lv=QVBoxLayout(left);apphead=QHBoxLayout();l=QLabel('软件使用时长');l.setObjectName('section');apphead.addWidget(l);apphead.addStretch();self.group_apps=QCheckBox('按分类');self.group_apps.toggled.connect(self.refresh);apphead.addWidget(self.group_apps);lv.addLayout(apphead);self.apps=QTreeWidget();self.apps.setMinimumHeight(220);self.apps.setHeaderLabels(['软件','前台时长','会话']);self.apps.setRootIsDecorated(False);self.apps.header().setSectionResizeMode(QHeaderView.Interactive);self.apps.setColumnWidth(0,210);self.apps.setColumnWidth(1,168);self.apps.setColumnWidth(2,126);lv.addWidget(self.apps);web=QLabel('网页浏览');web.setObjectName('section');lv.addWidget(web);self.browser=QTreeWidget();self.browser.setMinimumHeight(220);self.browser.setHeaderLabels(['网站','访问次数','最近访问']);self.browser.itemExpanded.connect(self.load_browser_pages);lv.addWidget(self.browser);splitter.addWidget(left)
        right=self.card();rv=QVBoxLayout(right);r=QLabel('做过的事（已合并文件噪声）');r.setObjectName('section');rv.addWidget(r);self.activities=QTreeWidget();self.activities.setMinimumHeight(480);self.activities.setHeaderLabels(['活动','说明','证据']);self.activities.setColumnWidth(0,300);self.activities.itemDoubleClicked.connect(self.open_path);rv.addWidget(self.activities);splitter.addWidget(right);splitter.setSizes([430,650]);v.addWidget(splitter,4);page.setMinimumHeight(1100);scroll=QScrollArea();scroll.setWidgetResizable(True);scroll.setFrameShape(QFrame.NoFrame);scroll.setWidget(page);return scroll
    def _wechat(self):
        page=QWidget();v=QVBoxLayout(page);headrow=QHBoxLayout();head=QLabel('今日收到的微信文件');head.setObjectName('section');headrow.addWidget(head);headrow.addStretch();headrow.addWidget(QLabel('类型'));self.wechat_filter=QComboBox();self.wechat_filter.addItems(['全部','文档','图片','压缩包','音视频','其他']);self.wechat_filter.currentTextChanged.connect(self.filter_wechat);headrow.addWidget(self.wechat_filter);v.addLayout(headrow);hint=QLabel('已自动过滤缓存、缩略图和临时文件。双击文件名可在资源管理器中定位。');hint.setObjectName('muted');v.addWidget(hint);split=QSplitter(Qt.Vertical);self.wechat_table=QTableWidget(0,6);self.wechat_table.setHorizontalHeaderLabels(['类型','文件名','大小','接收时间','备注','操作']);self.wechat_table.horizontalHeader().setSectionResizeMode(1,QHeaderView.Stretch);self.wechat_table.itemChanged.connect(self.wechat_note_changed);self.wechat_table.itemSelectionChanged.connect(self.show_wechat_summary);self.wechat_table.cellDoubleClicked.connect(self.open_wechat_file);split.addWidget(self.wechat_table);summary_card=self.card();sv=QVBoxLayout(summary_card);sh=QHBoxLayout();sl=QLabel('AI 文件摘要');sl.setObjectName('section');sh.addWidget(sl);sh.addStretch();self.wechat_progress=QProgressBar();self.wechat_progress.setRange(0,0);self.wechat_progress.setMaximumWidth(180);self.wechat_progress.hide();sh.addWidget(self.wechat_progress);self.wechat_status=QLabel('选择文件后可在这里查看分析结果');self.wechat_status.setObjectName('muted');sv.addLayout(sh);sv.addWidget(self.wechat_status);self.wechat_summary=QTextBrowser();self.wechat_summary.setMinimumHeight(190);sv.addWidget(self.wechat_summary);split.addWidget(summary_card);split.setSizes([430,260]);v.addWidget(split);return page
    def _snapshots(self):
        page=QWidget();v=QVBoxLayout(page);select=self.card();sv=QVBoxLayout(select);bar=QHBoxLayout();self.snap_a=QComboBox();self.snap_b=QComboBox();self.snap_a.setMinimumSize(280,64);self.snap_b.setMinimumSize(280,64);bar.addWidget(self.snap_a);arrow=QLabel('→');arrow.setObjectName('metric');bar.addWidget(arrow);bar.addWidget(self.snap_b);self.compare_btn=QPushButton('开始对比');self.compare_btn.setObjectName('primary');self.compare_btn.clicked.connect(self.compare_snapshots);bar.addWidget(self.compare_btn);delete=QPushButton('删除左侧快照');delete.clicked.connect(self.delete_snapshot);bar.addWidget(delete);sv.addLayout(bar);quick=QHBoxLayout();q=QPushButton('今天 vs 昨天');q.clicked.connect(self.quick_today);quick.addWidget(q);quick.addWidget(QPushButton('本周 vs 上周'));quick.addStretch();sv.addLayout(quick);v.addWidget(select)
        self.snap_progress=QProgressBar();self.snap_progress.setRange(0,0);self.snap_progress.hide();v.addWidget(self.snap_progress);stats=QHBoxLayout();self.diff_stats=[]
        for t,flt in [('📊 新增','仅新增'),('✏ 修改','仅修改'),('🗑 删除','仅删除'),('📦 大小变化','全部')]:
            c=self.card();c.setCursor(Qt.PointingHandCursor);x=QVBoxLayout(c);x.addWidget(QLabel(t));n=QLabel('0');n.setObjectName('metric');x.addWidget(n);c.mousePressEvent=lambda e,value=flt:self.action_filter.setCurrentText(value);stats.addWidget(c);self.diff_stats.append(n)
        v.addLayout(stats);ai=self.card();av=QVBoxLayout(ai);lab=QLabel('AI 差异解读');lab.setObjectName('section');av.addWidget(lab);self.diff_ai=QTextBrowser();self.diff_ai.setMinimumHeight(210);av.addWidget(self.diff_ai);self.diff_ai_btn=QPushButton('让 AI 分析这次变化');self.diff_ai_btn.setEnabled(False);self.diff_ai_btn.clicked.connect(self.run_diff_ai);av.addWidget(self.diff_ai_btn);v.addWidget(ai)
        filters=QHBoxLayout();self.action_filter=QComboBox();self.action_filter.addItems(['全部','仅新增','仅修改','仅删除']);self.action_filter.currentTextChanged.connect(self.render_diff);filters.addWidget(self.action_filter);self.type_filter=QComboBox();self.type_filter.addItems(['全部类型','代码','表格','文档','图片/媒体','安装包','压缩包','其他文件']);self.type_filter.currentTextChanged.connect(self.render_diff);filters.addWidget(self.type_filter);self.path_filter=QLineEdit();self.path_filter.setPlaceholderText('输入路径或文件名，实时筛选');self.path_filter.textChanged.connect(self.render_diff);filters.addWidget(self.path_filter,1);v.addLayout(filters);self.diff=QTreeWidget();self.diff.setHeaderLabels(['变化','路径','大小']);self.diff.setColumnWidth(1,650);v.addWidget(self.diff,1);return page
    def _history(self):
        page=QWidget();v=QVBoxLayout(page);bar=QHBoxLayout();info=QLabel('每日记录归档：左侧选日期，右侧查看当天完整复盘。');info.setObjectName('muted');bar.addWidget(info);bar.addStretch();week=QPushButton('生成周报');week.clicked.connect(lambda:self.run_period_report(7));bar.addWidget(week);month=QPushButton('生成月报');month.clicked.connect(lambda:self.run_period_report(30));bar.addWidget(month);self.history_range=QComboBox();self.history_range.addItems(['最近 7 天','最近 30 天']);self.history_range.currentIndexChanged.connect(self.load_history_days);bar.addWidget(self.history_range);push=QPushButton('推送选中日报');push.clicked.connect(self.repush);bar.addWidget(push);v.addLayout(bar);split=QSplitter(Qt.Horizontal);self.history_days=QListWidget();self.history_days.setMinimumWidth(180);self.history_days.currentItemChanged.connect(self.load_history_day);split.addWidget(self.history_days);self.history=QTextBrowser();split.addWidget(self.history);split.setSizes([220,850]);v.addWidget(split);return page
    def repush(self):
        key=self.config.get('serverchan_key','')
        if not key:return QMessageBox.information(self,'Server 酱','请先在设置中填写 SendKey。')
        item=self.history_days.currentItem();day=item.data(Qt.UserRole) if item else self.day();text=self.repo.summary(day)
        if not text:text=fallback_summary(aggregate(self.repo.file_events(day),self.repo.app_usage(day),self.repo.install_events(day)))
        try:
            from core.auto_tasks import push_serverchan
            push_serverchan(key,f"DayLens · {day} 日报",text,text[:60]);QMessageBox.information(self,'Server 酱','已使用分段 Markdown 样式推送。')
        except Exception as e:QMessageBox.warning(self,'推送失败',str(e))
    def update_date_text(self):
        week='一二三四五六日'[self.current_date.dayOfWeek()-1];self.date_btn.setText(f'{self.current_date.month()}月{self.current_date.day()}日 · 星期{week}  ▾')
    def pick_date(self):
        d=CustomDatePicker(self.repo,self.current_date,self);d.date_selected.connect(self.set_day);d.move(self.date_btn.mapToGlobal(QPoint(0,self.date_btn.height()+4)));d.exec()
    def set_day(self,date):self.current_date=date;self.update_date_text();self.refresh()
    def change_day(self,offset):
        self.current_date=self.current_date.addDays(offset);self.update_date_text();self.refresh()
    def day(self):return self.current_date.toString('yyyy-MM-dd')
    def periodic_tick(self):
        today=QDate.currentDate()
        if today!=self.last_system_date:
            # Follow the new day only when the page was still showing what was
            # "today" before midnight. A deliberately selected past day stays put.
            if self.current_date==self.last_system_date:
                self.current_date=today;self.update_date_text();self.rendered_day=None;self.refresh(True);self.statusBar().showMessage('日期已自动切换到今天',5000)
            self.last_system_date=today
        else:self.refresh()
    def refresh(self,force=False):
        if self.refresh_worker and self.refresh_worker.isRunning():
            self.refresh_pending=True;return
        self.refresh_request_id+=1;request_id=self.refresh_request_id
        day=self.day();cached=self.refresh_cache.get(day)
        if not force and cached and time.time()-cached[0]<60:
            if getattr(self,'rendered_day',None)==day:self.statusBar().showMessage('已是最新数据',2000);return
            payload=list(cached[1]);payload[0]=request_id;self.apply_refresh(tuple(payload));return
        self.statusBar().showMessage('正在后台刷新活动数据…')
        def collect(_):
            files=self.repo.file_events(day);apps=self.repo.app_usage(day);installs=self.repo.install_events(day);samples=self.repo.samples(day);focus=analyze(samples);browser=self.repo.browser_today(day);rows=self.repo.wechat_today(day);data=aggregate(files,apps,installs);data.update(focus=focus,browser=browser,notes=self.repo.notes(day));return request_id,day,data,apps,samples,focus,browser,rows,self.repo.summary(day)
        self.refresh_worker=Worker(collect);self.refresh_worker.done.connect(self.apply_refresh);self.refresh_worker.failed.connect(lambda e:self.statusBar().showMessage('刷新失败：'+e,8000));self.refresh_worker.finished.connect(self.refresh_finished);self.refresh_worker.start()
    def refresh_finished(self):
        if self.refresh_pending:self.refresh_pending=False;QTimer.singleShot(0,lambda:self.refresh(True))
    def apply_refresh(self,payload):
        request_id,day,self.data,apps,samples,focus,browser,rows,saved=payload
        if request_id!=self.refresh_request_id or day!=self.day():return
        self.refresh_cache[day]=(time.time(),payload);self.rendered_day=day
        vals=[duration(self.data['total_active']),str(self.data['app_count']),str(self.data['file_count']),str(len(self.data['clusters']))]
        for l,x in zip(self.metric_labels,vals):l.setText(x)
        self.metric_labels[0].setToolTip(f"今天电脑时间跨度 {focus.get('total_span_seconds',0)//60} 分钟，其中活跃 {focus.get('active_seconds',0)//60} 分钟")
        self.metric_labels[3].setToolTip('AI 归纳事件数：将大量文件变更按项目、目录和操作语义合并后的事件数量，不等于原始文件数。')
        self.apps.setUpdatesEnabled(False);self.apps.clear();mx=max([a['seconds'] for a in apps] or [1])
        category_nodes={}
        for a in apps:
            it=QTreeWidgetItem([a['display_name'],duration(a['seconds']),str(a['sessions'])]);it.setToolTip(0,a.get('window_title',''))
            if self.group_apps.isChecked():
                cat=self.config.get('app_categories',{}).get(a['process'].lower(),'其他');node=category_nodes.get(cat)
                if not node:node=QTreeWidgetItem([cat,'','']);category_nodes[cat]=node;self.apps.addTopLevelItem(node)
                node.addChild(it);node.setExpanded(True)
            else:self.apps.addTopLevelItem(it)
        self.apps.setUpdatesEnabled(True)
        self.timeline.set_sessions(focus.get('sessions',[]))
        if len(samples)<12:self.focus_score.setText('数据积累中');self.focus_bar.setValue(0);self.focus_detail.setText('持续使用约 1 分钟后显示专注度、切换次数和最长专注段')
        else:
            self.focus_score.setText(f"专注度 {focus['score']} 分");self.focus_bar.setValue(focus['score']);self.focus_detail.setText(f"切换 {focus['switch_count']} 次 · 平均连续使用 {focus_duration(focus['avg_focus'])} · 最长连续使用 {focus_duration(focus['longest_focus'])} · 对应软件：{focus['longest_app'] or '暂无'}")
            self.focus_detail.setToolTip('连续使用：从切换到某软件起，到切换到其他软件或进入空闲为止。对应软件是今天最长那一段所属的软件。')
        self.browser.setUpdatesEnabled(False);self.browser.clear()
        for x in browser:
            it=QTreeWidgetItem([x['domain'],str(x['visits']),datetime.fromtimestamp(x['last_visit']).strftime('%H:%M')]);it.setData(0,Qt.UserRole,x['domain']);it.setChildIndicatorPolicy(QTreeWidgetItem.ShowIndicator);self.browser.addTopLevelItem(it)
        self.browser.setUpdatesEnabled(True)
        rows=[x for x in rows if not (x['name'].lower().startswith('etilqs_') or '_thumb' in x['name'].lower() or x['name'].lower().endswith('_temp') or x['name'].lower().endswith('_t.dat') or Path(x['name']).suffix.lower() in {'.tmp','.temp','.part','.htm','.html'})];self.wechat_rows=rows
        if self.tabs.currentIndex()==1:self.render_wechat_rows()
        self.activities.setUpdatesEnabled(False);self.activities.clear()
        visible_clusters=self.data['clusters'][:200]
        for c in visible_clusters:
            top=QTreeWidgetItem([c['title'],c['description'],str(c['file_count'])]);top.setData(0,Qt.UserRole,c['path']);self.activities.addTopLevelItem(top)
            grouped={}
            for f in c['files']:grouped.setdefault(kind(f['path']),[]).append(f)
            for k,fs in sorted(grouped.items(),key=lambda z:-len(z[1])):
                samples='、'.join(Path(x['path']).name for x in fs[:3]);child=QTreeWidgetItem([f'{k}：{len(fs)} 个',f'示例：{samples}'+(f'，其余 {len(fs)-3} 个已合并' if len(fs)>3 else ''),c['path']]);child.setData(0,Qt.UserRole,c['path']);top.addChild(child)
        if len(self.data['clusters'])>len(visible_clusters):self.activities.addTopLevelItem(QTreeWidgetItem(['其余活动已折叠',f'为保持流畅，仅显示前 {len(visible_clusters)} 项；AI 仍按重要性归纳。',str(len(self.data['clusters'])-len(visible_clusters))]))
        self.activities.setUpdatesEnabled(True)
        text=saved or fallback_summary(self.data);self.set_rich_text(self.summary,text);self.ai_btn.setEnabled(self.ai_ready());self.ai_btn.setToolTip('' if self.ai_ready() else '请先在设置中配置 AI')
        if self.tabs.currentIndex()==2:self.load_snapshots()
        elif self.tabs.currentIndex()==3:self.load_history_days()
        self.statusBar().showMessage('已刷新 · 浏览器约 15 秒同步 · 后台监控运行中',4000)
    def on_tab_changed(self,index):
        if index==1:self.render_wechat_rows()
        elif index==2:self.load_snapshots()
        elif index==3:self.load_history_days()
    def render_wechat_rows(self):
        rows=getattr(self,'wechat_rows',[]);self.wechat_table.setUpdatesEnabled(False);self.wechat_table.blockSignals(True);self.wechat_table.setRowCount(len(rows))
        for i,x in enumerate(rows):
            vals=[x['file_type'],x['name'],self.size_text(x['size']),datetime.fromtimestamp(x['received']).strftime('%H:%M'),x['note']]
            for j,val in enumerate(vals):
                item=QTableWidgetItem(val);item.setData(Qt.UserRole,x['id']);item.setData(Qt.UserRole+1,x['path']);item.setData(Qt.UserRole+2,x.get('summary',''))
                if j!=4:item.setFlags(item.flags()&~Qt.ItemIsEditable)
                self.wechat_table.setItem(i,j,item)
            if Path(x['path']).suffix.lower() in {'.txt','.md','.docx','.pdf'}:
                b=QPushButton('分析');b.setEnabled(self.ai_ready());b.clicked.connect(lambda _,row=x:self.analyze_wechat(row));self.wechat_table.setCellWidget(i,5,b)
            else:
                b=QPushButton('仅展示');b.setEnabled(False);b.setToolTip('当前只分析 TXT、MD、DOCX 和可提取文字的 PDF');self.wechat_table.setCellWidget(i,5,b)
        self.wechat_table.blockSignals(False);self.wechat_table.setUpdatesEnabled(True);self.filter_wechat(self.wechat_filter.currentText())
    def set_rich_text(self,widget,text):
        body=markdown.markdown(text,extensions=['extra','nl2br'])
        css="""<style>body{font-family:'Microsoft YaHei UI';font-size:14px;line-height:1.85}h1,h2,h3{margin:14px 0 8px;color:#2D7FF9}p{margin:7px 0}li{margin:8px 0;padding-left:4px}strong{font-weight:700}hr{border:0;border-top:1px solid #dce2ec}</style>"""
        widget.setHtml(css+body)
    def size_text(self,n):
        for u in ['B','KB','MB','GB']:
            if n<1024:return f'{n:.0f} {u}'
            n/=1024
        return f'{n:.1f} TB'
    def load_browser_pages(self,item):
        if item.childCount():return
        for x in self.repo.browser_pages(self.day(),item.data(0,Qt.UserRole)):item.addChild(QTreeWidgetItem([x['title'] or x['url'],x['browser'],datetime.fromtimestamp(x['visit_time']).strftime('%H:%M')]))
    def wechat_note_changed(self,item):
        if item.column()==4:self.repo.update_wechat(item.data(Qt.UserRole),note=item.text())
    def filter_wechat(self,kind):
        for row in range(self.wechat_table.rowCount()):self.wechat_table.setRowHidden(row,kind!='全部' and self.wechat_table.item(row,0).text()!=kind)
    def show_wechat_summary(self):
        row=self.wechat_table.currentRow()
        if row<0:self.wechat_status.setText('选择文件后可在这里查看分析结果');self.wechat_summary.clear();return
        item=self.wechat_table.item(row,1);text=item.data(Qt.UserRole+2) or '还没有 AI 分析。点击右侧“分析”后，结果会保存并显示在这里。';self.wechat_status.setText(item.text());self.set_rich_text(self.wechat_summary,text)
    def open_wechat_file(self,row,column):
        if column!=1:return
        p=self.wechat_table.item(row,1).data(Qt.UserRole+1)
        if p and os.path.exists(p):QDesktopServices.openUrl(QUrl.fromLocalFile(os.path.dirname(p)))
    def analyze_wechat(self,row):
        p=Path(row['path']);ext=p.suffix.lower()
        try:
            if ext in {'.txt','.md'}:
                raw=p.read_text('utf-8',errors='ignore');text='【文件开头】\n'+raw[:5000]+'\n\n【文件末尾（重点分析）】\n'+raw[-20000:]
            elif ext=='.docx':
                import zipfile,re
                with zipfile.ZipFile(p) as z:
                    xml=z.read('word/document.xml').decode('utf-8','ignore');xml=xml.replace('</w:p>','\n').replace('</w:tr>','\n');raw=re.sub('<[^>]+>',' ',xml);raw=re.sub(r'[ \t]+',' ',raw);lines=[x.strip() for x in raw.splitlines() if x.strip()];text='【文档开头】\n'+'\n'.join(lines[:15])+'\n\n【文档最后内容（重点分析）】\n'+'\n'.join(lines[-80:])
            else:
                from pypdf import PdfReader
                pages=PdfReader(str(p)).pages;first=(pages[0].extract_text() or '') if pages else '';last=(pages[-1].extract_text() or '') if pages else '';text=f'【PDF 第 1 页】\n{first[:8000]}\n\n【PDF 最后 1 页（第 {len(pages)} 页，重点分析）】\n{last[-20000:]}'
            if len(''.join(text.split()))<20:raise ValueError('文档末页未提取到可读文字。它可能是扫描图片型 PDF，当前版本暂不做 OCR，请先将末页转为可选中文字的 PDF 或 TXT。')
        except Exception as e:return QMessageBox.warning(self,'无法读取',str(e))
        self.wechat_progress.show();self.wechat_status.setText(f'正在读取并分析“{p.name}”的真实内容…');self.wechat_summary.setHtml('<p>正在分析，请稍候…</p>');self.statusBar().showMessage(f'正在分析“{p.name}”的末页/末段内容…')
        worker=Worker(lambda q:summarize_document(self.config,p.name,text));worker.done.connect(lambda s:self.wechat_summary_done(row['id'],p.name,s));worker.failed.connect(self.wechat_failed)
        if not self.start_task('wechat_ai',worker):self.wechat_failed('已有微信文件正在分析，请等待完成。')
    def wechat_summary_done(self,wid,name,text):
        self.repo.update_wechat(wid,summary=text);self.wechat_progress.hide();self.wechat_status.setText(f'{name} · 分析完成');self.set_rich_text(self.wechat_summary,text);self.refresh(True)
    def wechat_failed(self,msg):self.wechat_progress.hide();self.wechat_status.setText('分析失败：'+msg);self.wechat_summary.setPlainText(msg)
    def ai_ready(self):return bool(self.config['ollama_model'] if self.config['ai_mode']=='ollama' else self.config['base_url'] and self.config['api_key'] and self.config['model'])
    def run_ai(self):
        if not self.ai_ready():return
        if self.tasks.get('daily_ai') and self.tasks['daily_ai'].isRunning():return
        self.ai_btn.setEnabled(False);self.ai_btn.setText('正在分析…');self.ai_status.setText('正在整理软件、网页和文件活动，请稍候…');self.ai_progress.show()
        worker=Worker(lambda p:generate(self.config,self.day(),self.data));worker.done.connect(self.ai_done);worker.failed.connect(self.work_failed);self.start_task('daily_ai',worker)
    def ai_done(self,text):self.repo.save_summary(self.day(),text);self.ai_btn.setText('生成 AI 今日总结');self.ai_status.setText('总结已生成');self.ai_progress.hide();self.refresh(True);self.statusBar().showMessage('AI 今日总结已生成',4000)
    def work_failed(self,msg):self.ai_btn.setText('生成 AI 今日总结');self.ai_btn.setEnabled(self.ai_ready());self.ai_status.setText('');self.ai_progress.hide();QMessageBox.warning(self,'操作失败',msg)
    def take_snapshot(self):
        self.snap_progress.show();self.statusBar().showMessage('正在拍摄快照… 已记录 0 个文件')
        def work(progress):
            data=capture(self.config['drives'],lambda n,p:progress(f'已记录 {n:,} 个文件：{p}'));return self.repo.add_snapshot(datetime.now().strftime('%Y-%m-%d %H:%M:%S'),data)
        worker=Worker(work);worker.progress.connect(self.statusBar().showMessage);worker.done.connect(self.snapshot_done);worker.failed.connect(self.work_failed)
        if not self.start_task('snapshot_capture',worker):self.statusBar().showMessage('已有快照正在拍摄',5000)
    def snapshot_done(self,_):self.snap_progress.hide();self.load_snapshots();self.statusBar().showMessage('快照已保存',5000);QToolTip.showText(self.mapToGlobal(self.rect().center()),'快照已保存',self)
    def load_snapshots(self):
        rows=self.repo.snapshots();cur_a=self.snap_a.currentData();cur_b=self.snap_b.currentData();self.snap_a.clear();self.snap_b.clear()
        for r in rows:
            dt=datetime.fromtimestamp(r['created']);week='一二三四五六日'[dt.weekday()];label=f"{dt:%m-%d} 周{week}  {dt:%H:%M}  · {r['file_count']:,} 个文件";self.snap_a.addItem(label,r['id']);self.snap_b.addItem(label,r['id'])
        if self.snap_b.count()>1:self.snap_b.setCurrentIndex(1)
    def compare_snapshots(self):
        a,b=self.snap_a.currentData(),self.snap_b.currentData()
        if not a or not b:return QMessageBox.information(self,'快照对比','请先拍摄至少两个快照。')
        if a==b:return QMessageBox.information(self,'快照对比','基准和对比快照不能相同。')
        ma,mb=self.repo.snapshot_meta(a),self.repo.snapshot_meta(b)
        if ma and mb and ma['created']>mb['created']:
            ia,ib=self.snap_a.currentIndex(),self.snap_b.currentIndex();self.snap_a.setCurrentIndex(ib);self.snap_b.setCurrentIndex(ia);a,b=b,a;QToolTip.showText(self.mapToGlobal(self.rect().center()),'已自动调整为：左侧较早，右侧较新',self)
        self.compare_btn.setText('对比中…');self.compare_btn.setEnabled(False);worker=Worker(lambda p:compare(self.repo.snapshot(a),self.repo.snapshot(b)));worker.done.connect(self.compare_done);worker.failed.connect(self.work_failed)
        if not self.start_task('snapshot_compare',worker):self.compare_btn.setText('开始对比');self.compare_btn.setEnabled(True)
    def compare_done(self,d):
        self.compare_btn.setText('开始对比');self.compare_btn.setEnabled(True);self.current_diff=d;sizes=sum(x.get('size',0) for x in d['added'])-sum(x.get('size',0) for x in d['deleted']);vals=[len(d['added']),len(d['modified']),len(d['deleted']),('+' if sizes>=0 else '-')+self.size_text(abs(sizes))]
        for l,x in zip(self.diff_stats,vals):l.setText(str(x))
        self.render_diff();self.diff_ai_btn.setEnabled(self.ai_ready())
    def render_diff(self,*_):
        if not getattr(self,'current_diff',None):return
        wanted={'仅新增':'added','仅修改':'modified','仅删除':'deleted'}.get(self.action_filter.currentText());wanted_type=self.type_filter.currentText();needle=self.path_filter.text().strip().lower();self.diff.clear()
        for typ,label in [('added','新增'),('modified','修改'),('deleted','删除')]:
            if wanted and wanted!=typ:continue
            rows=[x for x in self.current_diff[typ] if (wanted_type=='全部类型' or kind(x['path'])==wanted_type) and (not needle or needle in x['path'].lower())]
            if not rows:continue
            top=QTreeWidgetItem([f'{label}（{len(rows)}）','','']);self.diff.addTopLevelItem(top)
            for x in rows[:1000]:top.addChild(QTreeWidgetItem([label,x['path'],self.size_text(x.get('size',0))]))
            if len(rows)>1000:top.addChild(QTreeWidgetItem(['已限制展示',f'共 {len(rows):,} 条，为保持流畅仅渲染前 1,000 条','']))
    def delete_snapshot(self):
        sid=self.snap_a.currentData()
        if not sid:return
        if QMessageBox.question(self,'删除快照',f'确定删除左侧快照？\n{self.snap_a.currentText()}')!=QMessageBox.Yes:return
        self.repo.delete_snapshot(sid);self.current_diff=None;self.diff.clear();self.diff_ai.clear();self.load_snapshots();self.statusBar().showMessage('快照已删除',4000)
    def quick_today(self):
        if self.snap_a.count()>1:self.snap_a.setCurrentIndex(0);self.snap_b.setCurrentIndex(1)
    def run_diff_ai(self):
        if not getattr(self,'current_diff',None):return
        if self.tasks.get('snapshot_ai') and self.tasks['snapshot_ai'].isRunning():return
        self.diff_ai_btn.setEnabled(False);self.diff_ai_btn.setText('正在解读…');base=self.snap_a.currentText();comp=self.snap_b.currentText()
        worker=Worker(lambda p:generate_snapshot(self.config,base,comp,self.current_diff));worker.done.connect(self.diff_ai_done);worker.failed.connect(self.snapshot_ai_failed);self.start_task('snapshot_ai',worker)
    def snapshot_ai_failed(self,msg):self.diff_ai_btn.setText('重试 AI 分析');self.diff_ai_btn.setEnabled(True);self.diff_ai.setPlainText('分析失败：'+msg)
    def diff_ai_done(self,text):self.set_rich_text(self.diff_ai,text);self.diff_ai_btn.setText('重新分析');self.diff_ai_btn.setEnabled(True)
    def load_history_days(self,*_):
        if not hasattr(self,'history_days'):return
        current=self.history_days.currentItem().data(Qt.UserRole) if self.history_days.currentItem() else None;limit=7 if self.history_range.currentIndex()==0 else 30;days=self.repo.activity_days(limit);self.history_days.blockSignals(True);self.history_days.clear()
        for day in days:
            item=QListWidgetItem(day+('  · AI' if self.repo.summary(day) else '  · 本地'));item.setData(Qt.UserRole,day);self.history_days.addItem(item)
            if day==current:self.history_days.setCurrentItem(item)
        self.history_days.blockSignals(False)
        if self.history_days.count() and self.history_days.currentRow()<0:self.history_days.setCurrentRow(0)
    def load_history_day(self,item,*_):
        if not item:return
        day=item.data(Qt.UserRole);saved=self.repo.summary(day)
        if saved:self.set_rich_text(self.history,saved);return
        if self.history_worker and self.history_worker.isRunning():return
        self.history.setPlainText('正在整理这一天的记录…')
        def collect(_):return day,fallback_summary(aggregate(self.repo.file_events(day),self.repo.app_usage(day),self.repo.install_events(day)))
        self.history_worker=Worker(collect);self.history_worker.done.connect(lambda x:self.set_rich_text(self.history,x[1]) if self.history_days.currentItem() and self.history_days.currentItem().data(Qt.UserRole)==x[0] else None);self.history_worker.start()
    def auto_ai_refresh(self):
        if not self.config.get('auto_ai_analysis',True) or not self.ai_ready() or self.day()!=QDate.currentDate().toString('yyyy-MM-dd') or not self.data:return
        last=float(self.repo.get_kv('auto_ai_last',0) or 0)
        if time.time()-last<1800 or any(x.isRunning() for x in self.tasks.values()):return
        self.repo.set_kv('auto_ai_last',time.time());self.ai_status.setText('后台智能整理今日活动…');self.run_ai()
    def open_path(self,item,_):
        p=item.data(0,Qt.UserRole)
        if p and os.path.exists(p):QDesktopServices.openUrl(QUrl.fromLocalFile(p if os.path.isdir(p) else os.path.dirname(p)))
    def settings(self):
        d=SettingsDialog(self.config,self)
        if d.exec():
            old_auto=self.config['autostart'];self.config=d.value();save_config(self.config)
            if old_auto!=self.config['autostart']:set_autostart(self.config['autostart'],sys.executable)
            self.apply_theme();self.config_changed.emit(self.config);self.refresh(True)
    def quick_note(self):
        text,ok=QInputDialog.getMultiLineText(self,'快速记录','记录此刻的想法或事项：')
        if ok and text.strip():self.repo.add_note(text.strip());self.statusBar().showMessage('速记已保存，并会进入今日 AI 总结',4000);self.refresh(True)
    def global_search(self):
        query=self.search_box.text().strip()
        if not query:return
        self.search_box.setEnabled(False);self.search_box.setPlaceholderText('正在搜索…')
        worker=Worker(lambda p:self.repo.search(query));worker.done.connect(lambda rows:self.show_search_results(query,rows));worker.failed.connect(lambda e:(self.search_box.setEnabled(True),QMessageBox.warning(self,'搜索失败',e)));self.start_task('global_search',worker)
    def show_search_results(self,query,rows):
        self.search_box.setEnabled(True);self.search_box.setPlaceholderText('全局搜索  Ctrl+F')
        dialog=QDialog(self);dialog.setWindowTitle(f'搜索：{query}');dialog.resize(760,520);lay=QVBoxLayout(dialog);results=QTreeWidget();results.setHeaderLabels(['日期','类型','结果','详情']);results.setColumnWidth(0,105);results.setColumnWidth(1,90);results.setColumnWidth(2,230)
        for x in rows:results.addTopLevelItem(QTreeWidgetItem([x.get('date',''),x.get('kind',''),x.get('title',''),x.get('detail','')]))
        if not rows:results.addTopLevelItem(QTreeWidgetItem(['','','没有找到相关记录','可搜索文件名、路径、微信摘要、AI 总结和速记']))
        lay.addWidget(results);close=QPushButton('关闭');close.clicked.connect(dialog.accept);lay.addWidget(close);dialog.exec()
    def export_current(self,ext):
        path,_=QFileDialog.getSaveFileName(self,'导出当前记录',f'DayLens-{self.day()}{ext}',f'*{ext}')
        if not path:return
        if not path.lower().endswith(ext):path+=ext
        text=self.repo.summary(self.day()) or fallback_summary(self.data or {'apps':[],'clusters':[]})
        try:
            if ext=='.json':
                with open(path,'w',encoding='utf-8') as f:json.dump({'date':self.day(),'summary':text,'data':self.data},f,ensure_ascii=False,indent=2,default=str)
            elif ext=='.csv':
                with open(path,'w',encoding='utf-8-sig',newline='') as f:
                    w=csv.writer(f);w.writerow(['类型','名称','时长/文件数','说明'])
                    for x in self.data.get('apps',[]):w.writerow(['软件',x['display_name'],round(x['seconds']),'前台秒数'])
                    for x in self.data.get('clusters',[]):w.writerow(['活动',x['title'],x['file_count'],x['description']])
            elif ext=='.md':
                with open(path,'w',encoding='utf-8') as f:f.write(text)
            else:
                printer=QPrinter(QPrinter.HighResolution);printer.setOutputFormat(QPrinter.PdfFormat);printer.setOutputFileName(path);doc=QTextBrowser();self.set_rich_text(doc,text);doc.document().print_(printer)
            self.statusBar().showMessage('已导出：'+path,6000)
        except Exception as e:QMessageBox.warning(self,'导出失败',str(e))
    def run_period_report(self,days):
        if not self.ai_ready():return QMessageBox.information(self,'生成报告','请先在设置中配置 AI。')
        end=self.current_date;start=end.addDays(1-days);summaries=self.repo.summaries_between(start.toString('yyyy-MM-dd'),end.toString('yyyy-MM-dd'))
        data={'apps':[],'clusters':[{'type':'daily','title':x['day'],'description':x['markdown'][:600],'file_count':0,'first_seen':0,'last_seen':0} for x in summaries],'browser':[],'focus':{'active_seconds':days*1800,'total_span_seconds':days*1800,'idle_seconds':0},'notes':[]}
        self.history.setPlainText('正在汇总并生成报告，请稍候…');worker=Worker(lambda p:generate(self.config,f'{start.toString("yyyy-MM-dd")} 至 {end.toString("yyyy-MM-dd")}',data));worker.done.connect(lambda text:self.set_rich_text(self.history,text));worker.failed.connect(lambda e:self.history.setPlainText('生成失败：'+e));self.start_task('period_report',worker)
    def toggle_theme(self):self.config['theme']='dark' if self.config['theme']=='light' else 'light';save_config(self.config);self.apply_theme()
    def apply_theme(self):QApplication.instance().setStyleSheet(DARK if self.config['theme']=='dark' else LIGHT)
