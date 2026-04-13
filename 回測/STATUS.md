# 回測 — 現況速覽（給 AI agent 讀）

**更新日期**：2026-04-14
**詳細版**：看 `CONSULTANT_BRIEFING.md`（給人讀、含方法論細節與開放問題）

---

## 1. 在跑什麼

三個獨立的 autoresearch loop，每組研究一類資產：

| 資料夾 | 資產類別 | 標的數 |
|---|---|---|
| `autoresearch-forex/` | 外匯（7 major + 36 cross）| 43 |
| `autoresearch-commod/` | 商品（XAU/XAG/原油×2/天然氣）| 5 |
| `autoresearch-index/` | 股指（US500/DE40/JP225 等）| 15 |

**Loop 機制**：hypothesis-first → 改 `strategy.py` → 跑 `python evaluate.py` → 追加 `results.tsv` → 連續 15 次沒 `IMPROVED` 觸發 `PLATEAU_DETECTED` → 寫 `knowledge.md` → 複製到 `knowledge_history/session_N.md` → git commit → session 結束

---

## 2. 每組目前狀態（session 1 都已收斂）

| Group | 當前最佳 | composite | W1 / W2 | gap | 主要問題 |
|---|---|---|---|---|---|
| forex  | ADX>35 trend (EXP 15) | **1.213** | 2.52 / -0.09 | 2.60 ⚠️ | gap 偏高，W2 只打平 |
| commod | Vol-Adaptive RSI+BB+BB-Expanding (EXP106) | **3.210** | 3.27 / 3.15 | 0.12 ✅ | Session 3 最佳，DSR~0.999 |
| index  | Buy & Hold | **1.030** | 1.38 / 0.57 | 0.81 | 所有 active 都輸 B&H |

**各組詳細歷史**：
- `autoresearch-forex/knowledge_history/session_1.md` — ADX 研究完整軌跡，16 實驗
- `autoresearch-commod/knowledge_history/session_1.md` — RSI+BB 研究完整軌跡，43 實驗
- `autoresearch-commod/knowledge_history/session_2.md` — Vol-adaptive RSI 架構，42 實驗，composite 3.193
- `autoresearch-commod/knowledge_history/session_3.md` — BB-expanding 過濾器，21 實驗，composite 3.210
- `autoresearch-index/knowledge_history/session_1.md` — B&H 結論與 active 策略失敗分析，15 實驗

---

## 3. 評分系統（給不熟的 agent）

- **Walk-Forward 2 窗口**：W1 = 2024 Jul-Sep，W2 = 2024 Oct-Dec，前半年 Jan-Jun 只當 warm-up
- **Score**：composite = mean(w1, w2)，gap = |w1 - w2|
- **w1/w2 score** = 該窗口的 inverse-vol weighted portfolio Sharpe
- **硬罰則**：`pct_positive < 35%` 或 `n_symbols < 10` → composite - 10
- **Deflated Sharpe**：Bailey & Lopez de Prado，對多重檢定做修正，存在 `result['deflated_sharpe']`
- **benchmarks**：composite > 0.5 尚可 / > 1.0 good / > 2.0 very strong；gap < 2.0 穩定
- **細節在** `backtest_engine/scorer.py` 和 `autoresearch-{group}/evaluate.py`

---

## 4. 資料

- **訓練**：`1y_24_parquet/`（2024 全年、63 標的、OHLC + `tick_count` + `spread`）
- **黑盒**（禁止讀）：`1y_25_parquet/`（2025 資料，保留給最終驗證）
- **快取**：`.ohlcv_cache/`（resample 後快取）
- **提交紀錄**：`.blackbox_submissions.jsonl`（歷史黑盒驗證結果）

---

## 5. 你（AI agent）要幹嘛時

| 你想做的事 | 先讀什麼 | 然後 |
|---|---|---|
| 繼續某組的 session 2+ | 該組 `CLAUDE.md` + `program.md` + `knowledge_history/session_1.md` | 按 program.md 規則開始新實驗，編號從 (N-1)*50+1 |
| 全新研究想法 | 相關組的 `knowledge.md`（避免重跑已證偽方向）| 先寫 hypothesis，再實作 |
| 改評分系統 | `backtest_engine/scorer.py` + 每組 `evaluate.py` | ⚠️ 改動會讓三組過往 composite 無法直接比較，需要重跑 |
| 跨組組合（三組策略合成 portfolio）| 三組 knowledge + results.tsv | 這一步還沒做過，要從頭設計 |

---

## 6. 不要讀的資料夾（歷史/沙盒，已棄用）

- `autoresearch/` — v1（162 實驗，ER 方向，2025 黑盒 overfit 被證偽）
- `autoresearch-v2/` — v2（17 實驗，三組分組的前身，全標的版）
- `autoresearch-test/` — 純 loop reset 機制測試沙盒，沒有真實研究
- `monitor.sh` — 舊 bash auto-restart loop，因 Windows process 問題已不用

這些留著當歷史，**不要從它們拿策略或假設**（可能已被現役三組證偽）。

---

## 7. 禁令（硬規則）

- ❌ 不可讀 `1y_25_parquet/`
- ❌ 不可改 `evaluate.py` / `validate.py` / `backtest_engine/`（除非明確任務要求且有人類 review）
- ❌ 不可刪 `results.tsv` 歷史
- ❌ 不可在 autoresearch-{group}/ 內搞跨組邏輯（各組獨立）
