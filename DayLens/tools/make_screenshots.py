# -*- coding: utf-8 -*-
"""
Generate README screenshots with the REAL DayLens UI and FICTIONAL demo data.

The script redirects APPDATA to an isolated temp folder, seeds a realistic
demo day, renders the actual application and grabs every page. No personal
data is read or uploaded.

Usage:
    .venv\\Scripts\\python.exe tools\\make_screenshots.py
"""
import os, sys, time, tempfile, string
from datetime import datetime
from pathlib import Path

DAYLENS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(DAYLENS))
IMG = DAYLENS.parent / "docs" / "images"
IMG.mkdir(parents=True, exist_ok=True)

# --- isolate APPDATA BEFORE importing any project module -------------------
DEMO = Path(tempfile.mkdtemp(prefix="daylens-demo-"))
os.environ["APPDATA"] = str(DEMO)

from PySide6.QtWidgets import QApplication, QScrollArea
from PySide6.QtCore import Qt
from PySide6.QtGui import QPainter, QColor, QPen, QFont, QPixmap

from config.manager import load_config
from db.repository import Repository
from ui.main_window import MainWindow
from ui.settings_dialog import SettingsDialog
from core.snapshot import compare

DAY = datetime.now().strftime("%Y-%m-%d")

def ts(h, m=0):
    return datetime.now().replace(hour=h, minute=m, second=0, microsecond=0).timestamp()

# ---------------------------------------------------------------------------
# Demo content
# ---------------------------------------------------------------------------
SCHEDULE = [  # start, end, process, display, exe, title
    ("09:00", "09:24", "chrome.exe", "Google Chrome",
     r"C:\Program Files\Google\Chrome\Application\chrome.exe",
     "GitHub - xueze-ai/daylens · Qt Documentation"),
    ("09:24", "09:31", "WeChat.exe", "微信",
     r"C:\Program Files\Tencent\WeChat\WeChat.exe", "微信"),
    ("09:31", "10:48", "Code.exe", "Visual Studio Code",
     r"C:\Users\demo\AppData\Local\Programs\Microsoft VS Code\Code.exe",
     "timeline.py - daylens - Visual Studio Code"),
    ("10:56", "11:22", "chrome.exe", "Google Chrome",
     r"C:\Program Files\Google\Chrome\Application\chrome.exe",
     "PySide6 API Reference · Stack Overflow"),
    ("11:22", "12:01", "Code.exe", "Visual Studio Code",
     r"C:\Users\demo\AppData\Local\Programs\Microsoft VS Code\Code.exe",
     "main_window.py - daylens - Visual Studio Code"),
    ("13:05", "13:34", "explorer.exe", "文件资源管理器",
     r"C:\Windows\explorer.exe", "Documents\周报"),
    ("13:34", "14:10", "WINWORD.EXE", "Microsoft Word",
     r"C:\Program Files\Microsoft Office\root\Office16\WINWORD.EXE",
     "2026-10-06周报.docx - Word"),
    ("14:10", "14:47", "Code.exe", "Visual Studio Code",
     r"C:\Users\demo\AppData\Local\Programs\Microsoft VS Code\Code.exe",
     "auto_tasks.py - daylens - Visual Studio Code"),
    ("14:47", "14:59", "WeChat.exe", "微信",
     r"C:\Program Files\Tencent\WeChat\WeChat.exe", "微信"),
    ("14:59", "15:41", "chrome.exe", "Google Chrome",
     r"C:\Program Files\Google\Chrome\Application\chrome.exe",
     "Ollama docs · Python Packaging Guide"),
    ("15:41", "16:26", "Code.exe", "Visual Studio Code",
     r"C:\Users\demo\AppData\Local\Programs\Microsoft VS Code\Code.exe",
     "repository.py - daylens - Visual Studio Code"),
    ("16:26", "16:38", "EXCEL.EXE", "Microsoft Excel",
     r"C:\Program Files\Microsoft Office\root\Office16\EXCEL.EXE",
     "项目排期.xlsx - Excel"),
    ("16:38", "17:15", "Code.exe", "Visual Studio Code",
     r"C:\Users\demo\AppData\Local\Programs\Microsoft VS Code\Code.exe",
     "test_timeline.py - daylens - Visual Studio Code"),
    ("17:15", "17:40", "chrome.exe", "Google Chrome",
     r"C:\Program Files\Google\Chrome\Application\chrome.exe",
     "GitHub Actions · Hacker News"),
    ("17:40", "18:16", "Code.exe", "Visual Studio Code",
     r"C:\Users\demo\AppData\Local\Programs\Microsoft VS Code\Code.exe",
     "README.md - daylens - Visual Studio Code"),
]
IDLE = [("10:48", "10:56"), ("12:01", "13:05")]

# path, event, size(KB/MB marker via tuple), h:m
def KB(n): return n * 1024
def MB(n): return int(n * 1024 * 1024)

FILES = [
    (r"D:\Projects\daylens\main.py", "modified", KB(58), "09:34"),
    (r"D:\Projects\daylens\config\manager.py", "modified", KB(12), "09:38"),
    (r"D:\Projects\daylens\ui\main_window.py", "modified", KB(126), "09:46"),
    (r"D:\Projects\daylens\ui\settings_dialog.py", "modified", KB(38), "09:55"),
    (r"D:\Projects\daylens\ui\timeline.py", "created", KB(16), "10:02"),
    (r"D:\Projects\daylens\ui\timeline.py", "modified", KB(19), "10:30"),
    (r"D:\Projects\daylens\ui\widgets\date_picker.py", "modified", KB(14), "10:12"),
    (r"D:\Projects\daylens\core\aggregator.py", "modified", KB(11), "10:20"),
    (r"D:\Projects\daylens\core\focus.py", "modified", KB(7), "10:26"),
    (r"D:\Projects\daylens\ui\main_window.py", "modified", KB(129), "14:20"),
    (r"D:\Projects\daylens\core\auto_tasks.py", "created", KB(9), "14:18"),
    (r"D:\Projects\daylens\core\snapshot.py", "modified", KB(6), "14:40"),
    (r"D:\Projects\daylens\db\repository.py", "modified", KB(32), "15:02"),
    (r"D:\Projects\daylens\ai\client.py", "modified", KB(18), "15:30"),
    (r"D:\Projects\daylens\ui\timeline.py", "modified", KB(21), "15:20"),
    (r"D:\Projects\daylens\tests\test_timeline.py", "created", KB(8), "16:10"),
    (r"D:\Projects\daylens\ui\main_window.py", "modified", KB(131), "16:50"),
    (r"D:\Projects\daylens\README.md", "modified", KB(24), "17:20"),
    (r"D:\Projects\daylens\requirements.txt", "modified", KB(1), "17:25"),
    (r"C:\Users\demo\Documents\周报\2026-10-06周报.docx", "created", KB(246), "13:40"),
    (r"C:\Users\demo\Documents\周报\2026-10-06周报.docx", "modified", KB(251), "14:06"),
    (r"C:\Users\demo\Documents\会议纪要\1006会议纪要.txt", "created", KB(22), "14:52"),
    (r"C:\Users\demo\Documents\需求说明.md", "modified", KB(18), "15:48"),
    (r"C:\Users\demo\Desktop\项目排期.xlsx", "created", KB(96), "16:30"),
    (r"C:\Users\demo\Desktop\季度复盘.pptx", "modified", MB(4.2), "17:10"),
    (r"C:\Users\demo\Downloads\NoteNest-Setup-1.2.0.exe", "created", MB(92), "10:40"),
    (r"C:\Users\demo\Downloads\DayLens-v1.0.9.zip", "created", MB(53), "11:12"),
    (r"C:\Users\demo\Downloads\API参考文档.pdf", "created", MB(5.8), "15:55"),
    (r"C:\Program Files\NoteNest\NoteNest.exe", "created", MB(86), "16:42"),
    (r"C:\Program Files\NoteNest\resources.pak", "created", MB(12), "16:42"),
    (r"C:\Program Files\NoteNest\icudtl.dat", "created", MB(10), "16:43"),
    (r"C:\Program Files\NoteNest\ffmpeg.dll", "created", MB(4), "16:43"),
    (r"C:\Program Files\NoteNest\libGLESv2.dll", "created", MB(6), "16:43"),
    (r"C:\Program Files\NoteNest\locales\en-US.pak", "created", KB(420), "16:44"),
    (r"C:\Program Files\NoteNest\locales\zh-CN.pak", "created", KB(380), "16:44"),
    (r"C:\Program Files\NoteNest\resources\app.asar", "created", MB(28), "16:44"),
    (r"C:\Program Files\NoteNest\Uninstall NoteNest.exe", "created", MB(2), "16:45"),
    (r"C:\Program Files\NoteNest\vk_swiftshader.dll", "created", MB(18), "16:45"),
    (r"D:\OldBackups\archive-2025.iso", "deleted", MB(820), "17:32"),
    (r"C:\Users\demo\Downloads\旧版安装包.exe", "deleted", MB(36), "17:34"),
]

BROWSER = [  # h:m, domain, url, title
    ("09:02", "github.com", "https://github.com/xueze-ai/daylens", "GitHub - xueze-ai/daylens"),
    ("09:06", "github.com", "https://github.com/xueze-ai/daylens/pulls", "Pull requests · daylens"),
    ("09:10", "doc.qt.io", "https://doc.qt.io/qt-6/qpainter.html", "QPainter Class | Qt Widgets"),
    ("09:15", "doc.qt.io", "https://doc.qt.io/qt-6/qscrollarea.html", "QScrollArea Class"),
    ("09:19", "stackoverflow.com", "https://stackoverflow.com/questions/tagged/pyside6", "Newest 'pyside6' Questions"),
    ("09:23", "developer.mozilla.org", "https://developer.mozilla.org/docs/Web/JavaScript", "JavaScript | MDN"),
    ("10:57", "doc.qt.io", "https://doc.qt.io/qtforpython-6/", "Qt for Python Documentation"),
    ("11:01", "stackoverflow.com", "https://stackoverflow.com/questions/76098431", "PySide6 QThread example"),
    ("11:06", "github.com", "https://github.com/PySide/pyside-setup", "PySide/pyside-setup"),
    ("11:12", "pypi.org", "https://pypi.org/project/PySide6/", "PySide6 · PyPI"),
    ("11:18", "platform.openai.com", "https://platform.openai.com/docs", "OpenAI API Reference"),
    ("15:02", "ollama.com", "https://ollama.com/library/qwen2.5", "qwen2.5 | Ollama"),
    ("15:08", "docs.python.org", "https://docs.python.org/3.11/", "Python 3.11 documentation"),
    ("15:14", "packaging.python.org", "https://packaging.python.org/", "Python Packaging User Guide"),
    ("15:21", "github.com", "https://github.com/pyinstaller/pyinstaller", "pyinstaller/pyinstaller"),
    ("15:28", "www.reddit.com", "https://www.reddit.com/r/Python/", "r/Python - Reddit"),
    ("15:34", "news.ycombinator.com", "https://news.ycombinator.com/", "Hacker News"),
    ("16:02", "github.com", "https://github.com/xueze-ai/daylens/actions", "Actions · daylens"),
    ("17:17", "github.com", "https://github.com/xueze-ai/daylens/releases", "Releases · daylens"),
    ("17:22", "www.bing.com", "https://www.bing.com/search?q=pyinstaller+onedir", "pyinstaller onedir - Search"),
    ("17:28", "stackoverflow.com", "https://stackoverflow.com/questions/tagged/sqlite", "Newest 'sqlite' Questions"),
    ("17:34", "doc.qt.io", "https://doc.qt.io/qt-6/stylesheet.html", "Qt Style Sheets Reference"),
]

WECHAT = [  # h:m, name, type, size
    ("09:41", "项目需求文档V2.docx", "文档", KB(248)),
    ("09:52", "会议纪要-1006.txt", "文档", KB(22)),
    ("10:05", "现场勘查照片.jpg", "图片", MB(3.4)),
    ("10:31", "资料合集.zip", "压缩包", MB(86)),
    ("11:02", "产品演示录屏.mp4", "音视频", MB(142)),
    ("11:16", "产品手册.pdf", "文档", MB(5.8)),
    ("11:28", "说明文档.md", "文档", KB(9)),
    ("13:52", "海报终稿.png", "图片", MB(6.2)),
    ("14:20", "通话录音.mp3", "音视频", MB(8.8)),
    ("14:44", "头像素材.gif", "图片", MB(1.1)),
    ("15:12", "合同扫描件.pdf", "文档", MB(12)),
    ("15:36", "演示视频.mov", "音视频", MB(210)),
    ("16:48", "数据备份.7z", "压缩包", MB(340)),
    ("17:26", "接口定义.pdf", "文档", MB(2.6)),
]

NOTES = [("10:08", "时间线要加双击恢复全天的快捷键"),
         ("13:48", "周报里补上快照对比的进度"),
         ("17:40", "明天测试 Server 酱推送")]

TODAY_MD = """## 今日一句话

今天主要在开发 DayLens 的时间线缩放功能，并整理了周报与需求文档。

## 主要活动

1. 使用 Visual Studio Code 开发 DayLens，前台活跃约 3 小时 42 分钟。
2. 修改了时间线缩放、拖动与日期自动切换相关代码。
3. 使用浏览器查阅 Qt 与 PySide6 文档，访问约 48 次。
4. 使用 Word 编写本周工作周报，并处理了排期表格。
5. 微信收到 14 个文件，多为文档和图片。
6. 检测到安装了 NoteNest 1.2.0，目录出现 26 次变更。

> 结论均来自本机记录，证据不足处使用“可能”表述。
"""

DIFF_MD = """## 差异一句话

过去一天新增了时间线功能代码，并集中清理了旧备份文件。

## 变化解读

1. daylens 项目新增 8 个代码文件，修改 11 个文件。
2. 下载目录新增 NoteNest 安装包与 2 个压缩包。
3. Program Files 下新增完整的 NoteNest 程序目录。
4. 删除旧备份约 820 MB，属于集中清理行为。
5. 周报与排期等 3 个文档被修改。
"""

WECHAT_SUM_MD = """**文档用途**：DayLens 时间线模块的需求与交互说明。

**主要主题**：全天时间线的缩放、拖动与悬停提示规则。

**末段结论**：双击时间线应恢复全天视图，并在下方显示操作提示。

**关键要点**：

1. 滚轮以指针位置为中心缩放，最小可视范围 1 小时。
2. 悬停活动块显示精确到秒的起止时间与时长。
3. 缩放层级自动切换 2 小时至 15 分钟网格。
"""

PAST_MD = {
    "2026-10-05": "## 今日一句话\n\n修复了浏览器历史读取锁定的问题。\n\n## 主要活动\n\n1. 浏览器采集改为复制 History 副本后读取。\n2. 补充跨天自动快照检查逻辑。\n3. 使用 VS Code 前台活跃约 4 小时 10 分钟。\n",
    "2026-10-04": "## 今日一句话\n\n完成自绘日期选择器与全局搜索。\n\n## 主要活动\n\n1. 新增 CustomDatePicker 与记录日期蓝点。\n2. 全局搜索覆盖文件、微信与 AI 总结。\n3. 默认启用 GDI 字体渲染，解决乱码。\n",
    "2026-10-03": "## 今日一句话\n\n优化大数据库性能并完成 V1.0.7。\n\n## 主要活动\n\n1. 日期查询由约 1.7 秒降到约 0.1 毫秒。\n2. 取消启动全库 quick_check。\n3. 数据保留清理改为后台执行。\n",
    "2026-10-02": "## 今日一句话\n\n完善文件降噪与专注度统计。\n\n## 主要活动\n\n1. 加入目录与扩展名白名单、缓存黑名单。\n2. 30 秒内回到同一软件合并为连续工作段。\n3. AI 文案限制为 40 字以内短句。\n",
    "2026-10-01": "## 今日一句话\n\n修复多个闪退问题并稳定后台线程。\n\n## 主要活动\n\n1. 修复 QThread 引用被回收导致的闪退。\n2. 引入后台任务注册表管理异步任务。\n3. 快照差异明细每类最多渲染 1,000 条。\n",
}

# ---------------------------------------------------------------------------
def seed(repo):
    # window samples (5 s granularity) from the schedule + idle blocks
    for a, b, proc, disp, exe, title in SCHEDULE:
        t0 = ts(*map(int, a.split(":"))); t1 = ts(*map(int, b.split(":")))
        t = t0
        while t < t1:
            repo.add_sample(proc, disp, exe, title, t, 0); t += 5
    for a, b in IDLE:
        t0 = ts(*map(int, a.split(":"))); t1 = ts(*map(int, b.split(":")))
        t = t0
        while t < t1:
            repo.add_sample("__idle__", "空闲", "", "空闲", t, 1); t += 5
    # file events
    for path, etype, size, hm in FILES:
        h, m = map(int, hm.split(":")); t = ts(h, m)
        root = path[:3]
        repo.add_file_events([(path, etype, 0, size, t, t, root)])
    # browser history
    for hm, domain, url, title in BROWSER:
        h, m = map(int, hm.split(":"))
        repo.add_browser_rows([("chrome", "Default", url, domain, title, ts(h, m))])
    # wechat files
    for hm, name, ftype, size in WECHAT:
        h, m = map(int, hm.split(":"))
        p = rf"D:\DemoData\WeChat Files\wxid_demo\msg_file\2026-10\{name}"
        repo.add_wechat(p, name, size, ftype, ts(h, m))
    repo.db.execute("UPDATE wechat_files SET summary=? WHERE name=?",
                    (WECHAT_SUM_MD, "项目需求文档V2.docx"))
    repo.db.commit()
    # install events
    repo.add_install_event("NoteNest 1.2.0", "installed", "Windows 卸载注册表", ts(16, 44))
    repo.add_install_event("Microsoft Visual Studio Code", "updated", "Windows 卸载注册表", ts(11, 40))
    repo.add_install_event("旧版压缩工具 3.1", "uninstalled", "Windows 卸载注册表", ts(17, 2))
    # notes
    for hm, text in NOTES:
        h, m = map(int, hm.split(":")); repo.add_note(text, ts(h, m))
    # summaries / reports
    repo.save_summary(DAY, TODAY_MD)
    repo.save_daily_report(DAY, TODAY_MD, "开发时间线功能并整理周报", 0)
    for day, md in PAST_MD.items():
        repo.save_summary(day, md)
        repo.save_daily_report(day, md, md.splitlines()[2], 0)

def build_snapshots(repo):
    common = {
        r"D:\Projects\daylens\main.py": [58000, ts(18, 0) - 86400],
        r"D:\Projects\daylens\db\repository.py": [30000, ts(18, 0) - 86400],
        r"D:\Projects\daylens\ai\client.py": [16000, ts(18, 0) - 86400],
        r"D:\Projects\daylens\core\focus.py": [7000, ts(18, 0) - 86400],
        r"C:\Users\demo\Documents\需求说明.md": [16000, ts(18, 0) - 86400],
        r"C:\Users\demo\Desktop\项目排期.xlsx": [90000, ts(18, 0) - 86400],
        r"D:\OldBackups\archive-2025.iso": [MB(820), ts(18, 0) - 86400],
        r"C:\Users\demo\Downloads\旧版安装包.exe": [MB(36), ts(18, 0) - 86400],
    }
    A = dict(common)
    B = dict(common)
    for p in (r"D:\Projects\daylens\main.py", r"C:\Users\demo\Desktop\项目排期.xlsx",
              r"C:\Users\demo\Documents\需求说明.md"):
        B[p] = [A[p][0] + 2400, ts(18, 0)]
    for p, sz in [
        (r"D:\Projects\daylens\ui\timeline.py", KB(21)),
        (r"D:\Projects\daylens\core\auto_tasks.py", KB(9)),
        (r"D:\Projects\daylens\tests\test_timeline.py", KB(8)),
        (r"C:\Users\demo\Downloads\NoteNest-Setup-1.2.0.exe", MB(92)),
        (r"C:\Program Files\NoteNest\NoteNest.exe", MB(86)),
        (r"C:\Program Files\NoteNest\resources\app.asar", MB(28)),
        (r"C:\Users\demo\Documents\周报\2026-10-06周报.docx", KB(251)),
        (r"C:\Users\demo\Downloads\API参考文档.pdf", MB(5.8)),
    ]:
        B[p] = [sz, ts(18, 0)]
    for p in (r"D:\OldBackups\archive-2025.iso", r"C:\Users\demo\Downloads\旧版安装包.exe"):
        del B[p]
    id_a = repo.add_snapshot("自动快照 2026-10-05 18:00", A)
    id_b = repo.add_snapshot("自动快照 2026-10-06 18:00", B)
    repo.db.execute("UPDATE snapshots SET created=? WHERE id=?", (ts(18, 0) - 86400, id_a))
    repo.db.execute("UPDATE snapshots SET created=? WHERE id=?", (ts(18, 0), id_b))
    repo.db.commit()
    return A, B

# ---------------------------------------------------------------------------
def pump(ms=300):
    end = time.time() + ms / 1000
    while time.time() < end:
        QApplication.processEvents(); time.sleep(0.01)

def wait_worker(win):
    guard = 0
    while win.refresh_worker and win.refresh_worker.isRunning() and guard < 200:
        pump(100); guard += 1

def save(pix, name):
    pix.save(str(IMG / name)); print("saved", name)

def grab_all(win, payloads):
    sa = win.findChild(QScrollArea)
    win.resize(1280, 860); win.show(); wait_worker(win); pump(500)

    # --- Today tab, scroll positions ---
    win.tabs.setCurrentIndex(0); pump(400)
    sa.verticalScrollBar().setValue(0); pump(300)
    save(win.grab(), "01-overview.png")
    sa.verticalScrollBar().setValue(170); pump(300)
    save(win.grab(), "02-ai-review.png")
    sa.verticalScrollBar().setValue(300); pump(300)
    save(win.grab(), "03-apps-browser.png")
    sa.verticalScrollBar().setValue(sa.verticalScrollBar().maximum()); pump(300)
    save(win.grab(), "04-activities.png")
    save(sa.widget().grab(), "05-today-full.png")

    # --- WeChat ---
    win.tabs.setCurrentIndex(1); pump(500)
    for r in range(win.wechat_table.rowCount()):
        if win.wechat_table.item(r, 1).text() == "项目需求文档V2.docx":
            win.wechat_table.setCurrentCell(r, 1)
    pump(300)
    save(win.grab(), "06-wechat.png")

    # --- Snapshot compare ---
    win.tabs.setCurrentIndex(2); pump(500)
    # snapshots() sorts newest first; show older on the left as the baseline.
    if win.snap_a.count() > 1:
        win.snap_a.setCurrentIndex(1); win.snap_b.setCurrentIndex(0)
    A, B = payloads
    d = compare(A, B); win.current_diff = d; win.compare_done(d)
    win.set_rich_text(win.diff_ai, DIFF_MD)
    win.diff_ai_btn.setEnabled(True); win.diff_ai_btn.setText("重新分析")
    pump(300); win.diff.expandAll(); pump(300)
    save(win.grab(), "07-snapshot-diff.png")

    # --- History ---
    win.tabs.setCurrentIndex(3); pump(500)
    save(win.grab(), "08-history.png")

    # --- Settings dialog: AI tab + About tab ---
    dlg = SettingsDialog(win.config, win); dlg.resize(920, 620); dlg.show(); pump(400)
    dlg.tabs.setCurrentIndex(1); pump(300)
    save(dlg.grab(), "09-settings-ai.png")
    dlg.tabs.setCurrentIndex(6); pump(300)
    save(dlg.grab(), "10-about.png")
    dlg.close()

    # --- Dark mode hero ---
    win.tabs.setCurrentIndex(0); sa.verticalScrollBar().setValue(0); pump(200)
    win.config["theme"] = "dark"; win.apply_theme(); pump(400)
    save(win.grab(), "11-dark.png")

# ---------------------------------------------------------------------------
def make_grid(name, cells):
    """cells: list of (title, image filename). 2x2 window-card grid."""
    W, H, M, G = 1600, 990, 40, 32
    cw, ch = (W - 2 * M - G) // 2, (H - 2 * M - G) // 2
    canvas = QPixmap(W, H); canvas.fill(QColor("#F4F6FA"))
    p = QPainter(canvas); p.setRenderHint(QPainter.Antialiasing)
    p.setFont(QFont("Microsoft YaHei", 11))
    p.setPen(QColor("#748099"))
    p.drawText(QPixmap(W, H).rect(), Qt.AlignTop | Qt.AlignHCenter, "")
    for idx, (title, img_name) in enumerate(cells):
        r, c = divmod(idx, 2)
        x, y = M + c * (cw + G), M + r * (ch + G)
        # shadow
        p.setPen(Qt.NoPen)
        for k, alpha in ((6, 16), (4, 22), (2, 30)):
            p.setBrush(QColor(27, 39, 70, alpha))
            p.drawRoundedRect(x, y + k, cw, ch, 12, 12)
        # card
        p.setBrush(QColor("white")); p.setPen(QPen(QColor("#E1E7F0"), 1))
        p.drawRoundedRect(x, y, cw, ch, 12, 12)
        # header dots
        for i, col in enumerate(("#FF5F57", "#FEBC2E", "#28C840")):
            p.setBrush(QColor(col))
            p.drawEllipse(x + 18 + i * 16, y + 15, 10, 10)
        # title
        p.setPen(QColor("#2B3550")); p.setFont(QFont("Microsoft YaHei", 12, QFont.Bold))
        p.drawText(x, y + 4, cw, 40, Qt.AlignCenter, title)
        p.setPen(QPen(QColor("#EDF0F5"), 1)); p.drawLine(x + 1, y + 46, x + cw - 1, y + 46)
        # screenshot
        shot = QPixmap(str(IMG / img_name))
        area_w, area_h = cw - 28, ch - 46 - 26
        scaled = shot.scaled(area_w, area_h, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        sx = x + (cw - scaled.width()) // 2; sy = y + 46 + (area_h - scaled.height()) // 2 + 10
        p.setPen(QPen(QColor("#E6EAF1"), 1)); p.setBrush(QColor("#F7F9FC"))
        p.drawRoundedRect(sx - 4, sy - 4, scaled.width() + 8, scaled.height() + 8, 8, 8)
        p.drawPixmap(sx, sy, scaled)
    p.end()
    canvas.save(str(IMG / name)); print("saved", name)

# ---------------------------------------------------------------------------
def main():
    config = load_config()
    config["theme"] = "light"
    config["ai_mode"] = "ollama"; config["ollama_model"] = "qwen2.5:7b"
    repo = Repository(); seed(repo)
    payloads = build_snapshots(repo)
    app = QApplication.instance() or QApplication(sys.argv)
    win = MainWindow(repo, config)
    grab_all(win, payloads)
    make_grid("preview-grid-1.png", [
        ("今日总览 · 指标与全天时间线", "01-overview.png"),
        ("AI 今日复盘", "02-ai-review.png"),
        ("微信文件监控", "06-wechat.png"),
        ("快照对比 · AI 差异解读", "07-snapshot-diff.png"),
    ])
    make_grid("preview-grid-2.png", [
        ("软件时长 · 网页浏览", "03-apps-browser.png"),
        ("做过的事 · 语义活动归纳", "04-activities.png"),
        ("每日记录归档", "08-history.png"),
        ("深色模式", "11-dark.png"),
    ])
    print("done")

if __name__ == "__main__":
    main()
