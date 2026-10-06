from PySide6.QtWidgets import *
from PySide6.QtGui import QIntValidator
from PySide6.QtCore import QThread,Signal,Qt
class CallWorker(QThread):
    done=Signal();failed=Signal(str)
    def __init__(self,fn):super().__init__();self.fn=fn
    def run(self):
        try:self.fn();self.done.emit()
        except Exception as e:self.failed.emit(str(e))

class SettingsDialog(QDialog):
    def __init__(self,config,parent=None):
        super().__init__(parent);self.setWindowTitle('DayLens 设置');self.setMinimumSize(860,560);self.c=dict(config)
        root=QVBoxLayout(self);self.tabs=QTabWidget();self.tabs.setTabPosition(QTabWidget.North);self.tabs.setUsesScrollButtons(True);root.addWidget(self.tabs);general=QWidget();f=QFormLayout(general);self.tabs.addTab(general,'常规')
        self.theme=QComboBox();self.theme.addItems(['明亮','深色']);self.theme.setCurrentIndex(1 if config['theme']=='dark' else 0);f.addRow('外观主题',self.theme)
        box=QWidget();h=QHBoxLayout(box);h.setContentsMargins(0,0,0,0);self.drives=[]
        for d in ['C:\\','D:\\','E:\\']:
            c=QCheckBox(d[:2]);c.setChecked(d in config['drives']);self.drives.append((d,c));h.addWidget(c)
        h.addStretch();f.addRow('监控磁盘',box);self.auto=QCheckBox('登录 Windows 后自动启动');self.auto.setChecked(config['autostart']);f.addRow('开机自启',self.auto);days_row=QHBoxLayout();self.days=QLineEdit(str(config['retention_days']));self.days.setValidator(QIntValidator(1,3650,self));self.days.setMaximumWidth(100);days_row.addWidget(self.days);days_row.addWidget(QLabel('天'));days_row.addStretch();f.addRow('数据保留',days_row);self.idle=QComboBox();self.idle.addItems(['1 分钟','3 分钟','5 分钟','10 分钟']);vals=[1,3,5,10];self.idle.setCurrentIndex(vals.index(config.get('idle_minutes',5)) if config.get('idle_minutes',5) in vals else 2);f.addRow('空闲判定',self.idle)
        note=QLabel('数据全部保存在本机。只有主动生成总结时，结构化摘要才会发送到你配置的 AI 地址；不会发送文件内容。');note.setWordWrap(True);note.setObjectName('muted');f.addRow(note)
        ai=QWidget();af=QVBoxLayout(ai);self.tabs.addTab(ai,'AI 服务');self.mode=QComboBox();self.mode.addItems(['自定义 API','本地 Ollama']);self.mode.setCurrentIndex(1 if config['ai_mode']=='ollama' else 0);af.addWidget(QLabel('选择 AI 方式'));af.addWidget(self.mode);self.stack=QStackedWidget();af.addWidget(self.stack)
        api=QWidget();ap=QFormLayout(api);self.base=QLineEdit(config['base_url']);ap.addRow('API 地址',self.base);self.key=QLineEdit(config['api_key']);self.key.setEchoMode(QLineEdit.Password);ap.addRow('API Key',self.key);self.model=QLineEdit(config['model']);ap.addRow('模型',self.model);self.stack.addWidget(api)
        oll=QWidget();op=QFormLayout(oll);self.ollama=QLineEdit(config['ollama_url']);op.addRow('Ollama 地址',self.ollama);self.omodel=QLineEdit(config['ollama_model']);op.addRow('模型名',self.omodel);self.stack.addWidget(oll);self.mode.currentIndexChanged.connect(self.stack.setCurrentIndex);self.stack.setCurrentIndex(self.mode.currentIndex());test_ai=QPushButton('测试 AI 连接');test_ai.clicked.connect(self.test_ai);af.addWidget(test_ai)
        sources=QWidget();sf=QFormLayout(sources);self.tabs.addTab(sources,'数据来源');self.browser=QCheckBox('采集 Chrome / Edge / Firefox 历史');self.browser.setChecked(config.get('browser_history_enabled',True));sf.addRow('浏览器历史',self.browser);self.excludes=QPlainTextEdit('\n'.join(config.get('browser_excludes',[])));self.excludes.setMaximumHeight(80);sf.addRow('排除域名',self.excludes);self.wechat=QCheckBox('监控微信接收文件');self.wechat.setChecked(config.get('wechat_enabled',True));sf.addRow('微信文件',self.wechat);self.wechat_path=QLineEdit(config.get('wechat_path',''));choose=QPushButton('选择…');choose.clicked.connect(self.choose_wechat);row=QHBoxLayout();row.addWidget(self.wechat_path);row.addWidget(choose);sf.addRow('微信路径',row)
        focus=QWidget();fv=QVBoxLayout(focus);self.tabs.addTab(focus,'专注度说明');focus_text=QTextBrowser();focus_text.setHtml("""<h2>专注度怎么计算</h2><p>DayLens 每 5 秒采样一次前台软件。从切换到某软件开始，到切换至其他软件或进入空闲为止，算一段“连续使用”。</p><p><b>分数 = 100 - 切换惩罚 - 空闲惩罚</b></p><ul><li>每小时软件切换次数 × 0.8，最多扣 60 分。</li><li>空闲时间占比 × 100，最多扣 20 分。</li><li>分数最低为 0。切换越频繁、空闲占比越高，分数越低。</li></ul><h3>指标含义</h3><ul><li><b>平均连续使用</b>：所有非空闲会话的平均长度；不足 1 分钟时显示秒数。</li><li><b>最长连续使用</b>：当天最长的一段不切换前台软件的时间。</li><li><b>对应软件</b>：最长连续使用那一段所属的软件，例如 ChatGPT。它不是额外扣分项。</li></ul><p>例如：“平均 28 秒”说明窗口切换很频繁；以前向下取整会显示为 0 分钟，现在已改为秒数。</p>""");fv.addWidget(focus_text)
        advanced=QWidget();adv=QFormLayout(advanced);self.tabs.addTab(advanced,'高级');self.font_engine=QComboBox();self.font_engine.addItem('GDI（推荐，解决中文乱码）','gdi');self.font_engine.addItem('DirectWrite','directwrite');self.font_engine.addItem('FreeType','freetype');idx=self.font_engine.findData(config.get('font_engine','gdi'));self.font_engine.setCurrentIndex(max(0,idx));adv.addRow('字体渲染引擎',self.font_engine);restart=QLabel('更改后需重启 DayLens 才会生效。');restart.setObjectName('muted');adv.addRow('',restart);self.categories=QPlainTextEdit('\n'.join(f'{k}={v}' for k,v in config.get('app_categories',{}).items()));self.categories.setPlaceholderText('每行一条，例如：\ncode.exe=开发工具\nwinword.exe=办公');self.categories.setMaximumHeight(130);adv.addRow('软件分类',self.categories);vacuum=QPushButton('整理数据库并释放空间');vacuum.setToolTip('清理过期数据后执行 SQLite VACUUM。大型数据库可能需要较长时间。');vacuum.clicked.connect(self.vacuum_db);adv.addRow('数据库维护',vacuum)
        auto=QWidget();xf=QFormLayout(auto);self.tabs.addTab(auto,'自动日报');self.auto_ai=QCheckBox('后台智能更新今日总结（每 30 分钟最多一次）');self.auto_ai.setChecked(config.get('auto_ai_analysis',True));xf.addRow(self.auto_ai);self.autos=QCheckBox('每天自动生成总结');self.autos.setChecked(config.get('auto_summary',False));xf.addRow(self.autos);time_row=QHBoxLayout();parts=config.get('auto_summary_time','22:00').split(':');self.hour=QLineEdit(parts[0]);self.minute=QLineEdit(parts[1] if len(parts)>1 else '00');self.hour.setValidator(QIntValidator(0,23,self));self.minute.setValidator(QIntValidator(0,59,self));self.hour.setMaximumWidth(60);self.minute.setMaximumWidth(60);time_row.addWidget(self.hour);time_row.addWidget(QLabel('时'));time_row.addWidget(self.minute);time_row.addWidget(QLabel('分'));time_row.addStretch();xf.addRow('生成时间',time_row);self.server=QCheckBox('生成后通过 Server 酱推送');self.server.setChecked(config.get('serverchan_enabled',False));xf.addRow(self.server);self.sendkey=QLineEdit(config.get('serverchan_key',''));self.sendkey.setEchoMode(QLineEdit.Password);xf.addRow('SendKey',self.sendkey);test=QPushButton('测试推送');test.clicked.connect(self.test_push);xf.addRow('',test)
        about=QWidget();about_lay=QVBoxLayout(about);self.tabs.addTab(about,'关于');heading=QLabel('DayLens · 每日镜');heading.setStyleSheet('font-size:22px;font-weight:700');about_lay.addWidget(heading);desc=QLabel('个人电脑活动智能复盘工具');desc.setObjectName('muted');about_lay.addWidget(desc);card=QFrame();card.setObjectName('card');form=QFormLayout(card);form.setLabelAlignment(Qt.AlignLeft);form.addRow('软件名称',QLabel('DayLens（每日镜）'));form.addRow('版本',QLabel('V1.0.9'));form.addRow('作者',QLabel('薛泽（Xue Ze）'));repo=QLabel('<a href="https://github.com/xueze-ai">github.com/xueze-ai</a>');repo.setOpenExternalLinks(True);repo.setTextInteractionFlags(Qt.TextBrowserInteraction);form.addRow('项目主页',repo);form.addRow('技术架构',QLabel('Python + PySide6 + SQLite'));principle=QLabel('活动数据默认保存在本机；只有主动调用 AI 时才向用户配置的服务发送结构化摘要。');principle.setWordWrap(True);form.addRow('数据原则',principle);form.addRow('版权',QLabel('Copyright © 2026 薛泽（Xue Ze）'));about_lay.addWidget(card);about_lay.addStretch()
        b=QDialogButtonBox(QDialogButtonBox.Save|QDialogButtonBox.Cancel);b.button(QDialogButtonBox.Save).setText('保存');b.button(QDialogButtonBox.Cancel).setText('取消');b.accepted.connect(self.accept);b.rejected.connect(self.reject);root.addWidget(b)
    def choose_wechat(self):
        p=QFileDialog.getExistingDirectory(self,'选择 WeChat Files 文件夹',self.wechat_path.text())
        if p:self.wechat_path.setText(p)
    def test_push(self):
        if not self.sendkey.text().strip():return QMessageBox.information(self,'测试推送','请先填写 SendKey。')
        try:
            from core.auto_tasks import push_serverchan
            push_serverchan(self.sendkey.text().strip(),'DayLens 测试','这是一条 DayLens 测试消息。配置连接正常。','DayLens 测试成功');QMessageBox.information(self,'测试推送','发送成功。')
        except Exception as e:QMessageBox.warning(self,'测试推送失败',str(e))
    def test_ai(self):
        from ai.client import generate
        c=self.value();self.wait=QProgressDialog('正在连接 AI 服务…','',0,0,self);self.wait.setCancelButton(None);self.wait.setWindowTitle('测试 AI');self.wait.show();self.call_worker=CallWorker(lambda:generate(c,'连接测试',{'apps':[],'clusters':[],'browser':[],'focus':{}}));self.call_worker.done.connect(self.ai_test_ok);self.call_worker.failed.connect(self.ai_test_fail);self.call_worker.start()
    def ai_test_ok(self):self.wait.close();QMessageBox.information(self,'AI 连接','连接和鉴权成功。')
    def ai_test_fail(self,msg):self.wait.close();QMessageBox.warning(self,'AI 连接失败',msg)
    def vacuum_db(self):
        from db.repository import DB_PATH
        import sqlite3
        self.wait=QProgressDialog('正在整理数据库，请勿关闭程序…','',0,0,self);self.wait.setCancelButton(None);self.wait.setWindowTitle('数据库维护');self.wait.show()
        def work():
            db=sqlite3.connect(DB_PATH,timeout=60);db.execute('PRAGMA wal_checkpoint(TRUNCATE)');db.execute('VACUUM');db.close()
        self.call_worker=CallWorker(work);self.call_worker.done.connect(lambda:(self.wait.close(),QMessageBox.information(self,'数据库维护','整理完成。')));self.call_worker.failed.connect(lambda e:(self.wait.close(),QMessageBox.warning(self,'数据库维护失败',e)));self.call_worker.start()
    def value(self):
        vals=[1,3,5,10];auto_time=f"{int(self.hour.text() or 0):02d}:{int(self.minute.text() or 0):02d}";cats={};
        for line in self.categories.toPlainText().splitlines():
            if '=' in line:
                k,v=line.split('=',1);cats[k.strip().lower()]=v.strip()
        selected=[d for d,c in self.drives if c.isChecked()];from pathlib import Path;home=Path.home();watch=[str(home/x) for x in ('Desktop','Documents','Downloads','Pictures','Videos') if (home/x).exists()];watch += [d for d in selected if d[:1] in ('D','E')]
        self.c.update(theme='dark' if self.theme.currentIndex() else 'light',ai_mode='ollama' if self.mode.currentIndex() else 'openai',base_url=self.base.text().strip(),api_key=self.key.text().strip(),model=self.model.text().strip(),ollama_url=self.ollama.text().strip(),ollama_model=self.omodel.text().strip(),drives=selected,watch_dirs=watch,autostart=self.auto.isChecked(),retention_days=int(self.days.text() or 30),idle_minutes=vals[self.idle.currentIndex()],browser_history_enabled=self.browser.isChecked(),browser_excludes=[x.strip() for x in self.excludes.toPlainText().splitlines() if x.strip()],wechat_enabled=self.wechat.isChecked(),wechat_path=self.wechat_path.text().strip(),auto_ai_analysis=self.auto_ai.isChecked(),auto_summary=self.autos.isChecked(),auto_summary_time=auto_time,serverchan_enabled=self.server.isChecked(),serverchan_key=self.sendkey.text().strip(),font_engine=self.font_engine.currentData(),app_categories=cats);return self.c
