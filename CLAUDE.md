# 量化專題 — System Prompt

## 專案擁有者
施博瀚（Po-Han Shih）— 師大資工系大四，前 CMU Information Systems（休學返台）。
指導教授：紀博文（Prof. Po-Wen Chi），師大資工系。

## 題目（現行，2026-06 更新）

**中文財經 KOL 觀點作為選股因子：對 Alpha101 的增量資訊檢定**
*Chinese Financial KOL Opinions as a Stock-Selection Factor: Testing Incremental Information over Alpha101*

把台灣財經 KOL（Facebook）的自由文本，用 LLM 抽成標準化、可回測的結構化資料，再把 KOL 觀點當成一個**選股因子**，檢定它在**扣掉已知價量因子（Alpha101）之後**是否還有預測力 —— 也就是它帶來的是「動能以外的新資訊」，還是只是動能的重新包裝。

> **定位（誠實版）**：主要是「把既有方法搬到一個少有人做的乾淨樣本（繁中獨立 KOL）」（指導教授已認可此路徑）；額外加上兩個對手研究多半沒做的嚴謹度檢定 —— incremental IC vs Alpha101、條件穩健性。不主張發明新方法、不誇大 contribution。
>
> **刻意收斂**：不再嘗試量化 KOL 對市場的因果「影響力」（難以乾淨識別）；改為純粹把 KOL 當因子、檢定其增量資訊含量（可嚴格回測）。

## 方法（三步 Pipeline + 增量檢定）

1. **LLM-as-Formatter**：自由文本 → 4 欄位 schema `{timestamp, id, direction∈-1/0/+1, weight}`。LLM 只做格式化 + 實體消歧（台積 ≡ 2330 ≡ TSMC），**不輸出信心分數、不評分**。
2. **Walk-forward 權重**：`weight` = 該 KOL 在該則發文「之前」的歷史命中率（point-in-time，最少 30 筆才估、不足給 0.5）。嚴防 look-ahead。
3. **聚合成每日 KOL 因子**：對每檔股票彙總近期 KOL 訊號 → `f_kol`。
4. **Incremental IC vs Alpha101**（核心驗收，見下）。

### Incremental IC vs Alpha101（核心）
每個 rebalance 日、在橫斷面上：
- 橫斷面迴歸 `f_kol ~ A₁..Aₖ`（Alpha101 因子）→ 殘差 `e` = Alpha101 解釋不掉的部分
- `Incremental IC = corr(e, 未來報酬)`，逐日平均
- 比較 raw IC vs incremental IC；落差越小 → KOL 越獨立於價量
- 加 Deflated Sharpe 校正多重檢定
- 目標：incremental IC ≥ 0.03（baseline）／≥ 0.05（stretch）

⚠️ 現況：**incremental IC 的方法已設計，計算仍進行中**。目前 PoC 報的是 raw（pooled）IC，尚未扣 Alpha101。

## PoC 現況（2026-04，已完成、正面）
3 位 FB KOL（巴逆逆 8zz / 盤整之王 / Uncle 大叔）、1,685 觀點、404 標的、2024–2026。
- 純方向 hit 54.3%（p=0.003）；walk-forward 加權 IC 0.097（raw 的 ×2.1）；高信心過濾 Sharpe 1.65。
- weight 分位 hit rate 49% → 62%，證明 walk-forward 權重有預測力。
- 4 個 anomaly：KOL skill 不跨 domain、過度自信反而較差、8zz 是延遲跟隨者非反指標、多空 skill 不對稱（→ 之後要分 weight_long / weight_short）。

## 技術棧
Python 3.11+；pandas/NumPy；LLM 抽取（Claude）；Whisper（語音，目前先擱置不主推）；FinMind 台股 + yfinance 美股 OHLC；自建 walk-forward / 橫斷面因子引擎（`回測/factor_lab/`，目前跑美股、需接台股）。

## 關鍵檔案
- `docs/評審簡報_KOL量化平台_v4.md` — 方法論定案版（期中簡報基礎）
- `docs/西方文獻比較_2026-05-27.md` — 西方文獻對位 + 七維差異化矩陣
- `research/口頭討論講稿.md` — 對指導教授的差異化 framing 與防守問答
- `kol/docs/POC_results_2026-04-24.md` — PoC 完整實證
- `kol/scripts/build_clean_schema.py` / `eval_clean_schema.py` — walk-forward weight 與下游評估
- `回測/factor_lab/cs_engine.py` — 橫斷面 IC / 多空回測引擎

## 工作原則
1. 繁體中文（技術術語除外）。
2. 個人貢獻清晰 —— 每個決策都能解釋為什麼這樣選。
3. 誠實標注「已驗證」vs「進行中」，不誇大。
4. 邊做邊寫、有進度就呈現。

## 歷史脈絡（已棄用，勿沿用）
本專題四月初最早的題目是「基於多情境壓力分析的量化因子穩健性評估」（Alpha101 壓力測試 / 凸性分析 + autoresearch forex/commod/index，在 `回測/` 裡）。4/23–4/24 已 pivot 到現在的 KOL 題目。舊框架僅作歷史參考。
