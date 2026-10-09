# 整目录批量转存 + 目录下载（2026-09 实测，A股 60min/1min 全量）

单文件转存下载（`transfer select --fsid` + `download`）对几十上百个文件太慢。
**整目录一次转存 + 目录一次下载** 可把「文件数」次操作降到「目录数」次。

## 步骤

```bash
LINK="https://pan.baidu.com/s/...?pwd=xxxx"

# 1. 找到要转存的目录 fs_id（是目录的 fsid，不是里面文件的）
bdpan transfer list "$LINK" --source-dir "/上级目录" --page 1 --page-size 100 --json \
  | python3 -c "import json,sys; d=json.load(sys.stdin); [print(i['fs_id'], i['name'], 'DIR' if i['is_dir'] else 'FILE') for i in d['items']]"

# 2. 整个目录转存到自己网盘（target_dir 会自动创建）
bdpan transfer select "$LINK" --fsid "<目录fsid>" -d "my_batch/<子目录>/" --json
# status=submitted 是异步；errno=20013/111 目录创建失败可 sleep 3-5 重试

# 3. 确认转存落地（目录会包一层同名子目录：my_batch/<子目录>/<原目录名>/）
bdpan ls "my_batch/<子目录>" --json

# 4. 目录下载：bdpan download 目录 → **平铺**到本地目标目录（不建子目录）
bdpan download "my_batch/<子目录>/<原目录名>" "/本地/目标/目录/"
```

## 实测关键点

- **目录下载是平铺的**：`download <目录>` 落到本地目标目录后，里面文件直接在该目录，
  不保留目录层级。按月归档 9 个月目录 → 每个下载到各自本地月目录，正好符合归档布局。
- **转存异步**：submit 后 sleep 5-10 再 `bdpan ls` 确认文件出现，再 download；
  偶发 `errno=111 / 20013`（目录创建失败）→ sleep 3-5 重试一次通常成功。
- **同名文件必须分目录**：不同市场/来源常有同名 zip（如各市场的 `2020_60min.zip`）。
  转存到同一目标目录会被覆盖串扰 → 每个市场独立转存目录
  （`60m_hs / 60m_idx / 60m_bj / 1m`），下载校验 unzip -t 才能保证内容对。
- **price 上限**：`bdpan ls` 每页默认 1000；`transfer list` page-size 上限 100；
  当月归档目录文件不足 100，一页即可，不用翻页。
- **bdpan ls 只收 1 个位置参数**：想列多个路径要分开调用。
- **macOS 无 `timeout` 命令**：需要限时用 Python subprocess timeout 或直接跑。
- **下载速度**：官方 bdpan 受限速但单文件几十 MB 秒级；优先级按大到小排。
- **批处理脚本**：子进程逐文件 `bdpan download`，本地已有且 unzip 完好则 SKIP——
  天然幂等，中断重跑安全。脚本放 /tmp 或独立目录，勿放仓库。

## 批量落库（配合 TradingRazer2）

下载后的 zip 用 `sync-kline all_in_src --zip <多个zip>` 批量入库：

```bash
/Applications/TradingRazer2/bin/tradingrazer sync-kline all_in_src \
  --source taobao_2077 --interval 1h \
  --start-time 20200101 --end-time 20261231 --workers 1 \
  --zip /path/2020_60min.zip /path/2021_60min.zip ...
```

- `--zip` 支持一次多个（nargs=+）；`--workers 1` 稳（SQLite 单写者，全新增可默认 8）
- 1h 复用 60min 文件（vnpy 标准周期直读），适配器 `_INTERVAL_TO_CN` 已映射
- 幂等 upsert：中断重跑安全，不会重复/缺漏