# ROADMAP — 中文財經 KOL 量化專題

> 題目：中文財經 KOL 觀點作為選股因子：對 Alpha101 的增量資訊檢定
> 更新：2026-06-15　｜　狀態圖例：🔴未開始　🟡進行中　🟢完成

---

## P0 — Incremental IC vs Alpha101（核心驗收）🔴

**這是整個題目標題在主張、但目前還沒做的那個數字。** 海報 Experimental Results 上的 ⚠ 註記指的就是這條。

### 為什麼是核心
目前 PoC 報的是 **raw IC**（hit 54.3%、IC 0.097、Sharpe 1.65），證明「KOL 有可交易訊號 + walk-forward 加權有效」。但這些數字**無法排除「KOL 只是在喊已經在漲的股票」= 動能**，而動能早被 Alpha101 收錄。
→ 必須把 `f_kol` 對 Alpha101 正交化，看殘差還剩多少預測力（incremental IC）。**剩 → 真有新資訊；不剩 → 只是動能換包裝（誠實的 null result，也是可寫的結論）。**

### 方法（每個 rebalance 日、橫斷面）
1. 橫斷面迴歸 `f_kol ~ A₁..Aₖ`（Alpha101 因子）→ 殘差 `e` = Alpha101 解釋不掉的部分
2. `Incremental IC = corr(e, 未來報酬)`，逐日平均
3. 比較 raw IC vs incremental IC；落差越小 → KOL 越獨立於價量
4. 加 **Deflated Sharpe** 校正多重檢定
5. 驗收門檻：incremental IC ≥ 0.03（baseline）／≥ 0.05（stretch）

### 現有 hooks（程式與資料都在）
- `f_kol` 因子：`kol/scripts/build_clean_schema.py` → `kol/data/clean_schema.jsonl`（1,739 筆 4 欄位 + walk-forward weight）
- 橫斷面 IC / 多空引擎：`回測/factor_lab/cs_engine.py`
- Alpha101 因子計算：`回測/factor_lab/factors.py`、`run_factors.py`
- 下游評估範式：`kol/scripts/eval_clean_schema.py`

### 卡點 / 待補
- **factor_lab 目前跑美股，需接台股 OHLC**（FinMind）才能在 404 個台股標的上算 Alpha101。
- Alpha101 多數公式需要量價齊全的日資料；先確認台股資料覆蓋度。
- 把 `f_kol`（KOL 因子）對齊到 factor_lab 的橫斷面 panel（日期 × 標的）格式。

### 完成定義
跑出一個 incremental IC 數字（即使是 null），把海報 Experimental Results 的 ⚠ 換成正式結果列；主張從「進行中」升級為「已驗證 / 已證偽」。

---

## P1 — 次要 / 強化（皆非海報必需）

- 🔴 **多空分離 weight_long / weight_short**：PoC anomaly 顯示高 weight KOL「看多」hit 66%、但「看空」只有 27.8% —— 多空 skill 不對稱，應分開建 weight。
- 🔴 **條件穩健性測試**：分市場狀態（多頭/空頭/盤整）、分產業、分 KOL 子集看 IC 是否穩定（對手研究多半沒做，是差異化點之一）。
- 🔴 **台股資料層接入**：FinMind 台股 OHLC → factor_lab，P0 也依賴此項。
- 🔴 **擴大 KOL 樣本**：目前 3 位（巴逆逆 8zz / 盤整之王 / Uncle 大叔），擴增可增強橫斷面 ranking 統計力。

## 探索性分岔（與顧問討論後再定）
- **NLP/IE 方向**：把 LLM extract 升級為 fine-tuned BERT，做對比實驗（方法論貢獻）。
- **純 quant 方向**：多因子組合模型 + 更嚴格回測。
- PoC 資料層兩條都已支援。

---

## 已完成 🟢
- PoC（2026-04）：3 KOL · 1,685 觀點 · 404 標的 · 2024–2026；raw 結果正面（見 `kol/docs/POC_results_2026-04-24.md`）。
- LLM-as-Formatter + walk-forward 權重 pipeline（`kol/`）。
- 期末海報 `KOL_Poster_v4.pptx`（clone Anomaly 參照格式，全英文）。
