# macOS 系统设置：面板在哪、怎么证实、怎么带用户到位

适用：用户问「怎么关掉 macOS 的某个功能」「这个开关在哪儿」。交付物是**准确的面板路径 + 那个面板里的原文标签**，不是文件改动。

## 回答顺序（先定面板，再定内容）
1. 先用 Apple 官方 guide 拿功能与选项原文（`support.apple.com/guide/<app>/...`、`support.apple.com/en-us/<article>`）：它告诉你**有哪些开关、各自决定什么**，这是判据；但它常按 iOS 写（"Settings > General > AutoFill & Passwords"），macOS 的层级不能照抄。
2. 在本机核对面板身份与它在这一版里的名字（下面命令）。
3. 用深链把那个面板打开给用户看，并在回答里说明你开了什么、最后一下要他自己点。

## 面板 = ExtensionKit 扩展
```bash
# 已安装面板的域；域的名字就是面板 bundle id
defaults domains | tr ',' '\n' | grep -iE 'Settings\.extension'

# 每个 .appex 一页；显示名与扩展点在这里
ls /System/Library/ExtensionKit/Extensions/
plutil -p "/System/Library/ExtensionKit/Extensions/<Pane>.appex/Contents/Info.plist" \
  | grep -iE 'CFBundleDisplayName|CFBundleIdentifier|legacyBundleIdentifier|UTTypeIdentifier|EXExtensionPointIdentifier'
```
- `EXExtensionPointIdentifier = com.apple.Settings.extension.ui` ⇒ 它是系统设置页；`CFBundleDisplayName` 是侧边栏显示的页名；`legacyBundleIdentifier`（如 `com.apple.preferences.password`）能把老资料里的路径对上这一页。
- **系统自带 app 的面板不在上面那个目录里**：`/System/Library/ExtensionKit/Extensions/<Pane>.appexlist` 是 JSON，把 `/System/Cryptexes/App/System/Library/CoreServices/<Pane>SettingsExtension.appex` 映射进来（Passwords 面板就是这样）。所以对 Passwords 一类面板 `find` 不到是正常的，去 `.appexlist` 找；运行中的进程路径会显示成 `/System/Volumes/Preboot/Cryptexes/...`。
- **一页可以带多个 UTTypeIdentifier**（同一扩展同时供 "Passwords" 与 "AutoFill & Passwords" 两处）。所以"页面标题"和"侧边栏条目"不必然同名——用户的定位词要用第 3 步从本机取。

## 面板在这一版里叫什么、搜什么词
```bash
D="/System/Cryptexes/App/System/Library/CoreServices/PasswordsSettingsExtension.appex"
ls "$D/Contents/Resources/en.lproj"                       # 里面有 *.searchTerms
plutil -convert json -o - "$D/Contents/Resources/en.lproj/AutoFillAndPasswords.searchTerms"
plutil -convert json -o - "$D/Contents/Resources/en.lproj/Localizable.strings"
```
- `*.searchTerms`（JSON，`Options.localizableStrings[].title / .index`）= 用户在系统设置搜索框里搜哪些词会跳到该页（实测：title `AutoFill & Passwords`，index `autofill, password manager`）。**把 "在系统设置里搜 X" 写进回答**，比断言侧边栏在 General 下面还是在 Passwords 下面稳。
- `.strings` / `.lproj` 都是二进制 plist：`strings -a` 与 `grep -r` 都看不到文本（会返回空），必须 `plutil -convert json -o - <file>` 再过滤。

## 深链打开 + 确认落在哪一页
```bash
open "x-apple.systempreferences:com.apple.Passwords-Settings.extension"
pgrep -lf LaunchArguments | grep -i password     # 面板进程带 -LaunchArguments <base64>
```
- 解出来的 JSON 形如 `{"serviceName":"com.apple.Passwords-Settings.extension","type":2,"enhancedSecurity":false}`：`type:2` = 系统设置页，`type:1` = 小组件/其他扩展。base64 是无 padding 的，解码前补 `=`。
- 这条 `pgrep -lf LaunchArguments` 也能一次看清当前开着哪些设置页（`AppleIDSettings`、`GeneralSettings`、`PrivacySecurity` …），用来判断"我刚才那一下到底开了什么"。
- **副作用要说**：深链会在用户屏幕上真的开一个窗口。不要偷偷开，也不要为了取证去截一个会列出他密码的面板——隐私优先于证据；需要内容判据就用官方 guide。

## 别指望用脚本点 UI（授权边界）
- `osascript` 的 System Events：读进程名可以；`keystroke` 报 `1002 … 不允许发送按键`，读窗口 `position/size` 报 `-1719 … 不允许辅助访问`。**不要设计"用 AppleScript 点开关 / 读窗口标签"的流程**；正确做法是深链打开 + 让用户点最后一下，并在回答里明确"最后一下需要你手动"。
- 用户自己的偏好 plist 也可能读不到：Safari 的在 `~/Library/Containers/com.apple.Safari/Data/Library/Preferences/com.apple.Safari.plist`，受 TCC 保护（`couldn't be opened because you don't have permission`）。这类不要 sudo 绕，转官方 guide 取证。
- 系统设置项的存放位置不一定在某个 `defaults` 域里（有些值走 keychain/别的 store）——找不到键名不代表用户没设过，别据此下"当前是开/关"的结论。

## 行标签/选项名从哪读：共享 UI framework 的 lproj
面板 appex 的 `Localizable.strings` 常常只有一个页面标题；整套行标签、开关名、下拉选项名在共享的 UI framework 里：
```bash
R=/System/Cryptexes/OS/System/Library/PrivateFrameworks/PasswordManagerUI.framework/Versions/A/Resources
plutil -convert json -o - "$R/zh_CN.lproj/Localizable.strings" > /tmp/ui_zh.json   # zh_HK / zh_TW / en 同理
python3 -c "import json;d=json.load(open('/tmp/ui_zh.json'));[print(repr(k),'->',repr(v)) for k,v in d.items() if '保存' in str(v)]"
```
一次拿到：开关名（`自动填充密码和通行密钥`）、下拉选项名（`登录时询问` / `登录时不询问`）、说明灰字、"排除的网站"清单文案，**以及侧边栏子项名**（`AutoFill Password (view title)` / `自动填充密码`）——后者可用来解释用户截图左栏里那些条目。用户跑中文界面就必须给中文标签，英文原名附在括号里。

## 界面 → 偏好键：让用户切一下，看谁被写
```bash
# 用户刚切完某个控件
find ~/Library -mmin -20 -type f -name '*.plist' | grep -iE 'passw|auth|safari'
plutil -p ~/Library/Preferences/com.apple.Passwords.plist | grep -iE 'save|ask|fill'   # → "PasswordSavingBehavior" => 1
```
- 这是"UI 控件 ↔ 偏好域/键"最快的映射（实测一次即中），比猜侧边栏层级或翻文档有用。
- 读 plist 文件本身，不用 `defaults read`（daemon 缓存可能滞后）。
- 键名+值只证明**存在这条设置**，不解释语义。

## 选项语义：读不到控制流，用"选项集合 + 状态实测"收口
- **读得到**：选项集合、选项名、说明灰字（framework lproj）。**读不到**：控制流——cryptex 里的框架磁盘上只剩 `Resources/` + `_CodeSignature/`，Mach-O 在 dyld 共享缓存里，`strings`/`grep`/`find <Name>` 一律落空。
- 因此**不要**用标签起名或第三方博客断言"这个选项会保存/不会保存"。本类问题的定法：
  1. **看选项集合覆盖什么语义**：只有 `询问 / 不询问` 两个值、全系统文案里没有任何"不保存/不再保存"的取值 ⇒ 该下拉**不可能**表示"不保存"（"不会保存"那句只属于"排除的网站"清单页）。
  2. **剩下的只能实测，且要设计成"状态会变"**：让用户在该设置下走一次真实流程（例如浏览器里提交一个假登录），再看应用里**有没有多出一条记录**。不要设计成"看说明文字会不会变"——设置页灰字常常是静态的（实测切换选项前后一字未变，用户当场回「没有任何变化」）。
  3. 自己跑不了（要用户敲键盘/点浏览器）就把实验写清、结论标未验证，同时给一条**与语义无关也成立**的替代路径（例：官方明文写着"保存你在网站上输入的用户名和密码"的那个浏览器勾选项）。
- 官方 guide 常漏掉新加的选项（Passwords 的 `保存密码：` 一行在 Apple"更改密码设置"页里就没有）；**漏掉 ≠ 不存在**，别因为 guide 没写就否认用户屏幕上的东西。

## 回答形状（本类问题）
- 一次只交付用户问的那 1–2 个控件，每个**一句话说清它管哪个方向**（读＝自动填充 / 写＝保存）。把三四个面板并列 + 机制解释会被回「你讲了一大堆，我也没搞懂」。
- 用户已经截图给你看的面板：只讲**这个面板里有什么、没有什么**；"你要的那个控件不在这里"要点名，然后才指向别处。
- 用到未验证的语义就明说未验证，并给一条可观察的验证；不要把从博客抄来的结论说成事实。自己判断错了，第一句先认「我说反了」，再给修正结论。
- 顺带点出与该功能竞争的同类工具（用户装了第三方密码管理器时，总闸那一页同时就是"用哪个 App 做自动填充"的选择处）。
- 挖到底的边界：**行标签/选项名值得挖**（framework lproj，一次 grep）；**pref key 值得挖**（`find -mmin` 一次即得，是判据之一）；**控制流不值得挖**（磁盘上没有二进制），改用一次状态实测。别去反解 dyld 共享缓存。

