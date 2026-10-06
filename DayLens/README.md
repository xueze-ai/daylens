# DayLens（每日镜）V1.0.1

## V1.0.1 Hotfix 3

- 日期、保留天数和自动日报时间改为纯数字控件，避免系统字体导致乱码。
- 专注度分数改为独立文字，进度条不再绘制异常百分比。
- 日常数据刷新、AI 生成和 AI 连接测试均在后台线程运行。
- AI 总结增加行距、段落间距和列表样式，生成时显示进度与状态。
- 微信文件页增加类型筛选。
- 应用限制为单实例，再次启动会激活已打开的窗口。

DayLens 是本地优先的 Windows 个人电脑活动复盘工具。它从启动后开始持续记录前台软件使用时长和文件系统增量事件，再把底层噪声聚合成人能理解的活动，例如“在 VS Code 中开发某项目”“处理了项目中的文档”“安装或更新了某软件”。

## 直接使用

交付目录为 `dist/DayLens/`，双击 `DayLens.exe`。程序关闭主窗口后继续驻留系统托盘；右键托盘图标可退出。

## 核心模块

- `core/file_monitor.py`：基于 watchdog / ReadDirectoryChangesW 监控 C、D、E 盘，事件以每 50 条或 10 秒批量写入 SQLite，无 15000 条上限。
- `core/window_tracker.py`：每 5 秒采样前台窗口，将连续相同进程合并为会话，得到实际前台时长。
- `core/installer_tracker.py`：对比 Windows 卸载注册表快照，识别安装、卸载和版本更新。
- `core/aggregator.py`：把原始文件事件按软件目录、下载目录、项目目录和文件类型预聚合；GUI 默认只显示语义活动。
- `core/snapshot.py`：拍摄全盘路径、大小和修改时间快照，并比较新增、修改和删除。
- `ai/client.py`：统一支持 OpenAI 兼容 API 与本地 Ollama。只发送预聚合摘要，不发送文件内容或完整路径列表。
- `db/repository.py`：SQLite WAL 存储、日期查询、快照与保留期清理。
- `ui/main_window.py`：今日复盘、软件时长、活动证据、快照对比和每日历史。

## V1.0.1 追加模块

### A · 浏览器历史

`core/browser_tracker.py` 每 10 分钟复制并读取 Chrome、Edge 与 Firefox 的历史数据库，避免浏览器文件锁；按域名聚合展示，并支持设置排除域名。AI 只接收 Top 10 域名摘要。

### B · 全天时间线

`ui/timeline.py` 将前台软件和空闲会话画成 0–24 时横向色块。同一软件保持固定颜色，悬停显示软件、起止时间和时长。

### C · 专注度分析

`core/focus.py` 根据真实会话计算切换次数、平均专注、最长专注、碎片化指数与 0–100 分评分，并展示在今日概览。

### D · 空闲检测

`core/window_tracker.py` 使用 Windows `GetLastInputInfo` 判断空闲。阈值可设为 1/3/5/10 分钟；空闲不计入软件时长，并在时间线中显示为灰色。

### E · 自动日报

`core/auto_tasks.py` 按设置时间自动生成日报，可选通过用户自己的 Server 酱 SendKey 推送。凭证不会内置，输入框以密码形式显示。

### 微信文件

`core/wechat_tracker.py` 使用同一套 watchdog 机制监控微信接收目录；默认尝试自动发现，也支持设置自定义目录。界面只展示文件信息和用户备注，不伪造发送者或聊天来源。

### 自动快照与差异解读

每天首次启动自动拍摄一次快照，也可以手动立即拍摄。快照计算在后台运行并持续显示已记录文件数；差异页提供新增、修改、删除和空间变化概览，并可把预聚合差异交给 AI 解读。

## 隐私边界

不截图、不录屏、不记录键盘、不监控网络流量。数据位于 `%APPDATA%\DayLens\daylens.db`。只有用户主动点击“生成 AI 今日总结”时，才调用用户自己配置的接口。

## 构建

在 PowerShell 中运行 `setup-build.ps1`，然后运行 `build.bat`。使用 Python 3.11、PySide6 和 PyInstaller `--onedir --windowed`。
