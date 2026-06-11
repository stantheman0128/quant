# HANDOFF — 跨電腦轉移筆記（筆電 → 桌機）

> 建立日期：2026-06-11
> 用途：把這個量化專題從目前這臺筆電轉移到自家桌機繼續做
> Repo：https://github.com/stantheman0128/quant.git （branch: `master`）

---

## 0. 一句話總結

**GitHub 上的 `origin/master` 才是最新、最完整的版本（截至 2026-05-27 的 `ebddefa`）。**
桌機只要 `git clone` 就拿到主體；另外手動補 `.env` 密鑰與被 gitignore 的原始資料即可。

---

## 1. 轉移當下的機器狀態（為什麼會搞混）

| | 舊筆電（local） | GitHub（origin/master） |
|---|---|---|
| commit | `851a8c6` | `ebddefa`（領先 2 個 commit） |
| 追蹤檔案 | 23 個（多為 markdown） | 138 個（完整專案） |

- 舊筆電是一份**殘缺/落後**的 checkout，**不是**進度最前面的那臺。
- GitHub 已含：`kol/` 全套 pipeline、完整 `回測/backtest_engine/`、`src/`、資料與圖表。

### 只存在於舊筆電、GitHub 沒有的檔案（轉移前要處理）
1. `research/口頭討論講稿.md`（2026-05-13，跟老師面談講稿）— **要保留 → 已 commit + push**
2. `__v2.pptx`（根目錄）— 與 `kol/__v2.pptx` 重複，未保留

---

## 2. `git clone` 不會帶過去的東西（被 .gitignore 擋）

桌機 clone 後仍需**手動**補：

- **`.env`** — API 金鑰／密鑰。從舊機複製，或依 `kol/.env.example` 重建。**最關鍵。**
- 音檔：`*.mp3 *.wav *.mp4 *.mov`（podcast 原始音檔）→ 重新下載或從雲端搬。
- 行情／歷史資料：`*.parquet`、`回測/1y_*/`、`回測/data/`、`**/.ohlcv_cache/` → 用腳本重新抓（Yahoo / broker）。
- 模型權重：`**/models/`、`*.safetensors *.pt` → whisper 轉錄模型會自動重抓。
- `*.jsonl` 匯出、`**/*_report.html`、`**/output/` → 由腳本重新產生。

> 注意：很多資料其實**有**進 git（`kol/data/gooaye.xml`、`tw-stock-list.json`、`kol/transcription/segments*.json`、轉錄稿、PNG 圖），所以 clone 下來已相當可用。

---

## 3. 桌機開機步驟（Setup）

```powershell
# 1) 取得程式碼
git clone https://github.com/stantheman0128/quant.git
cd quant

# 2) Python 環境（專案用 Python 3.11+）
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

# 3) 密鑰：把舊機的 .env 複製過來，或照 kol/.env.example 填
copy ..\path-to-old\.env .\kol\.env   # 視實際位置調整

# 4) 補資料（被 gitignore 的部分，依需要）
#    - 行情 parquet：跑 回測/backtest_engine/convert_to_parquet.py 之類腳本
#    - podcast 音檔 / 轉錄：kol/transcription/ 內腳本
```

驗證：`git log --oneline -5` 應看到 `ebddefa ...` 為最新。

---

## 4. 專題狀態速覽（接手時先讀這些）

這個題目經過數次 pivot，**目前主線 = 中文財經 KOL 觀點抽取與結構化建模**（早期的 Alpha101 壓力測試、autoresearch forex/commod/index 都已是歷史脈絡）。

接手請依序讀：
- `docs/評審簡報_KOL量化平台_v4.md` — 最新的題目定位／方法論（v4 收斂版）
- `research/口頭討論講稿.md` — 與指導教授面談的 framing 與防守問答（文獻 gap、與過去研究的三大差別）
- `kol/docs/POC_results_2026-04-24.md` — PoC 實證結果
- `回測/CONSULTANT_BRIEFING.md` / `回測/STATUS.md` — 早期回測系統的方法論與狀態（歷史脈絡）
- `CLAUDE.md` — 專案 system prompt（含早期 Alpha101 框架，部分已過時）

關鍵程式（都在 GitHub，不在舊筆電）：
- `kol/sources/{facebook,podcast,price}.py` — 資料來源
- `kol/extract/llm.py`、`kol/run_extract.py` — LLM 結構化抽取
- `kol/transcription/` — podcast 轉錄（whisper）
- `kol/poc/`、`kol/scripts/` — PoC 分析、評估、繪圖
- `回測/backtest_engine/` — 自建回測引擎

---

## 5. 日常多機協作（之後兩臺都用時）

- **單一真相來源 = GitHub。** 每次開工先 `git pull`，收工 `git push`。
- 密鑰、原始音檔、大型資料**不進 git**（已被 .gitignore 擋），靠雲端或腳本各機重建。
- 換機前養成 `git status` 確認沒有未 commit 的東西被留在某一臺。
