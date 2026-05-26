# 量化策略自動研究系統 — 顧問 Briefing

**日期**：2026-04-13
**作者**：施博瀚
**目的**：請顧問評估當前系統設計與執行方向是否合理，標出盲點與風險

---

## TL;DR

我正在跑一個假設驅動的自動化策略研究系統。核心循環是：agent 寫假設 → 改 `strategy.py` → 跑 walk-forward 評分 → 記錄 → 連續 15 次沒改善就 plateau，寫 knowledge.md、清 context、下一個 session 繼續。資料是 2024 年全年、63 個標的（外匯 43 + 商品 5 + 指數 15）、4h 頻率。

為了避免「用同一套策略 fit 全部資產類別」的拉低效應，我把研究拆成三個平行的資料夾（forex / commodity / index）各自獨立跑。三組都已完成 session 1：

- **外匯**：收斂於 ADX > 35 trend following，composite = **1.213**（首度正向突破）、W1=2.52 / W2=-0.09、gap=2.6 偏高
- **商品**：收斂於 RSI(21) + BB(1.8σ) MR，跨標的 portfolio_sharpe = **2.37** 很強，但因只有 5 個標的觸發硬罰則 → composite = -7.6
- **指數**：收斂於 Buy & Hold，composite = **1.03**，所有 active 策略都輸 B&H

**我最想跟你討論的**：
1. 評分系統的硬罰則（`pct_positive < 35%` 或 `n_symbols < 10` → `-10`）是否過嚴，導致商品組「真的賺錢但分數慘」
2. 指數只剩 B&H 是系統性問題（評分框架排斥 active）還是現實（2024 指數就是單邊上漲）
3. Walk-Forward 僅兩窗口（各 3 個月）是否樣本太小
4. 「連續 15 次沒 IMPROVED 即 plateau」的判定合理嗎
5. 假設驅動 + knowledge 旋進 的 loop 設計，有沒有明顯的 failure mode 我沒想到

---

## 1. 系統架構

### 1.1 資料層

- **原始資料**：`回測/1y_24/` 和 `回測/1y_25/`（CSV）、`1y_24_parquet/` 和 `1y_25_parquet/`（Parquet 快取）
- **欄位**：OHLC + `tick_count`（流動性代理）+ `spread`（真實買賣價差）
- **Agent 只能讀 `1y_24_parquet`**（2024 訓練），`1y_25_parquet` 為 2025 黑盒，保留給最終驗證
- **2024 資料劃分**：
  - Warm-up：Jan-Jun（6 個月，算 EMA / BB / RSI 等指標）
  - W1 test：Jul-Sep（3 個月）
  - W2 test：Oct-Dec（3 個月）

### 1.2 回測引擎 `backtest_engine/`

| 檔案 | 行數 | 用途 |
|---|---|---|
| `engine.py` | 170 | 向量化回測、防 lookahead（`signal.shift(1)`）、扣真實 spread + commission |
| `scorer.py` | 132 | 跨標的組合 Sharpe + 硬罰則 + Deflated Sharpe Ratio |
| `metrics.py` | — | Sharpe、Sortino、MDD、AR |
| `data_loader.py` | — | parquet 讀取、resample、快取 |
| `strategy.py` | — | `Strategy` 基底類別，策略須實作 `generate_signals(df) -> Series[1,-1,0]` |
| `auto_research.py` | 270 | 早期版本的 auto-loop（現在不用了，由 autoresearch-* 接手）|
| `app.py`, `cli.py`, `optimizer.py`, `black_box.py`, `visualizer.py` | — | CLI 工具與視覺化（非主線）|

**關鍵設計**（`engine.py:124-140`）：

```python
# 防 lookahead：用前一期信號乘當期報酬
shifted_signals = signals.shift(1).fillna(0)
strategy_returns = shifted_signals * price_returns

# 扣成本：commission + 真實 spread
signal_changes = shifted_signals.diff().fillna(0).abs()
spread_cost = signal_changes * (prices['spread'] / prices['close'] / 2).fillna(0)
cost = signal_changes * commission + spread_cost
strategy_returns = strategy_returns - cost
```

### 1.3 評分系統 `scorer.py`

**Composite score** 的定義見 `scorer.py:51-96`：

```
composite = portfolio_sharpe                   # 若 n_symbols ≥ 10 且 pct_positive ≥ 35%
         = portfolio_sharpe - 10              # 否則（硬罰則）

portfolio_sharpe = 該窗口內 inverse-vol weighted 組合報酬的年化 Sharpe
pct_positive    = 該窗口內 Sharpe > 0 的標的比例
```

**Walk-forward 合成**（`evaluate.py:200-225`）：

```
w1_score = 對 Jul-Sep 套用上述評分
w2_score = 對 Oct-Dec 套用上述評分
final_composite = mean(w1_score, w2_score)
gap = |w1_score - w2_score|      # 跨 regime 穩定性指標
```

**Deflated Sharpe Ratio**（`scorer.py:99-131`）：
- Bailey & Lopez de Prado 的多重檢定修正
- 輸入 observed Sharpe、試過的策略數（從 `results.tsv` 算）、樣本數
- 輸出 p-value：observed Sharpe 真實的機率
- 當前所有策略 DSR 都很低，因為實驗次數已經上升但 composite 多數為負

### 1.4 Autoresearch Loop `autoresearch-{group}/`

每組資料夾結構相同：

```
autoresearch-{group}/
├── CLAUDE.md                # 給 agent 看的規則（hypothesis-first, 禁止偷看 2025 資料等）
├── program.md               # 詳細 loop 步驟
├── strategy.py              # agent 會改，必須實作 create_strategy()
├── evaluate.py              # 不可改，跑評分
├── validate.py              # 不可改，保留給最終 2025 驗證
├── results.tsv              # 實驗歷史（追加，不覆寫）
├── knowledge.md             # 當前 session 的累積知識
└── knowledge_history/
    └── session_N.md         # 歷史 session 的凍結快照
```

**單一實驗流程**（`program.md`）：

1. **HYPOTHESIS**（必須先寫）
   - OBSERVATION：觀察到的市場現象
   - REASONING：經濟機制 + 數學依據
   - PREDICTION：預期 composite / W1 / W2 / pct_positive 變化
   - FALSIFICATION：什麼結果會證偽這個假設

2. **IMPLEMENT**：改 `strategy.py`，限制 ≤4 個可調參數、≤2 個出場條件

3. **TEST**：`python evaluate.py 2>&1 | tee run.log`

4. **VALIDATE**：比對 prediction / falsification，判定 `IMPROVED` / `REJECTED` / `FAILED`

5. **RECORD**：追加到 `results.tsv`，欄位包括 hypothesis 摘要、是否被證偽（yes/no/partial）、狀態、描述

**Session 與 Plateau**：

- PLATEAU_DETECTED = 連續 15 筆 `results.tsv` 都沒 `IMPROVED`（`evaluate.py:115-128`）
- 觸發 plateau 時 agent 自己：
  1. 重寫 `knowledge.md`（整理 verified findings、verified failures、next session 方向）
  2. 複製到 `knowledge_history/session_N.md`
  3. `git commit`，然後結束 session
- 新 session 開始時先讀 `knowledge.md` 再開始新實驗，避免重試已證偽的方向

### 1.5 為什麼拆三組跑？

先跑過一版 `autoresearch-v2/`（全 63 個標的一起跑，Session 1、17 個實驗）。最佳策略 `Hybrid Squeeze + MR + VWMA exit`：

```
composite = -0.019, gap = 0.021   # 跨 regime 極穩，但沒轉正
```

拆解 W2 的 asset group breakdown 後發現：

| 資產組 | n | W2 portfolio_sharpe |
|---|---|---|
| forex_cross | 36 | **+3.32** |
| forex_major | 7  | +1.23 |
| index | 15 | +0.77 |
| commodity | 5  | **−2.62** ← 主要拖累 |

結論：讓一套參數同時 fit 外匯、商品、指數，會被「最不合」那組拖垮 0.3-0.5 composite。分開研究讓每組有空間找自己合適的 signal family，最後再 portfolio 組合（這一步還沒做）。

---

## 2. 三組現狀

### 2.1 Forex（autoresearch-forex/）

**範圍**：43 個標的（7 major + 36 cross）

**狀態**：Session 1 已收斂、16 個實驗（EXP 0-15）、`knowledge_history/session_1.md` 已凍結

**當前 `strategy.py`**：`HighADX_Trend_4h`（EXP 15，session best）

```python
# autoresearch-forex/strategy.py
class ResearchStrategy(Strategy):
    name = "HighADX_Trend_4h"
    # 參數：adx_period=14, adx_threshold=35.0  (只有 2 個參數)
    # 進場：ADX > 35 時跟隨 +DI/-DI 方向
    # 出場：ADX 跌回 35 以下
```

**績效**：

```
composite = 1.213          # >1.0 = good
W1 = 2.516                 # Jul-Sep 趨勢市表現極強
W2 = -0.089                # Oct-Dec 震盪市幾乎打平
gap = 2.605                # ⚠️ 偏高，跨 regime 不穩
total_trades = 795         # 低交易頻率
```

**核心假設驗證**：「ADX > 35 隱式挑選 major pairs」成立。36 個 cross 在 W2 幾乎不觸發 ADX>35，天然被過濾掉。EXP 11（ADX>25）composite 只有 0.436，閾值拉到 35 直接把 trades 從大量減到 795 次，composite 衝到 1.21。

**Session 1 驗證過的發現**：
- **ADX 趨勢勝過所有其他 signal family**：連最低標準 ADX>25 都贏 MR、EWMAC、Donchian、autocorr
- **W2 forex_major 結構性為正**：所有 trend 實驗中 W2 major median_sharpe 都在 0.82-1.48，很穩
- **Trade count 決定一切**：EXP 2（10444 trades）→ composite -8.23；EXP 15（795 trades）→ +1.21
- **Forex 完全不適合 MR**：EXP 6-10 全部 fail，W1 趨勢市會把 MR 撞爛到 -15

**Session 1 已證偽的方向**：
- 純 BB MR、Symmetric MR、bounce confirm、z-score MR — 全 W1 崩
- EWMAC（不管快慢）、Donchian — crosses 拖累 W2
- Return autocorrelation、spread filter、ATR regime filter、tick count filter — 都 fail
- ER regime switching — 跟商品組一樣反而破壞價值

**這組最需要顧問看的**：
1. gap=2.6 太高 — W1=2.52 很強但 W2=-0.09 幾乎沒用。如果 2025 上半年長得像 W2（震盪），這策略會退化。是否該犧牲 W1 來換 W2 的穩定？
2. Forex 異質性高（major 穩、cross 難），是否該再拆成 forex-major 和 forex-cross 兩組獨立研究？
3. Session 2 的 agent 自己提議方向：ADX 閾值 30/32（介於 25 和 35）、VWMA exit、不對稱進出場（35 入 / 25 出）— 這些優先級你覺得對嗎？

### 2.2 Commodity（autoresearch-commod/）

**範圍**：5 個標的（XAUUSD, XAGUSD, USOIL, UKOIL, NATGAS）

**狀態**：Session 1 已收斂、43 個實驗、`knowledge_history/session_1.md` 已凍結

**當前 `strategy.py`**：`RSI21_BB18_4h`（EXP 28，best-of-session）

```python
# autoresearch-commod/strategy.py
class ResearchStrategy(Strategy):
    name = "RSI21_BB18_4h"
    # 參數：rsi_window=21, bb_period=20, bb_std=1.8, tick_ratio=0.75
    # 進場：long if RSI<35 & close<BB_lower & tick_ok & spread_ok
    #       short if RSI>75 & close>BB_upper & (同上)
    # 出場：RSI 回到 50
```

**績效**：

```
composite = -7.627    # 注意是負的
gap = 0.684
W1 = 2.031            # 很好
W2 = 2.725            # 很好
portfolio_sharpe = 2.37
```

**⚠️ 評分矛盾**：portfolio_sharpe 2.37 是三組最強，但 composite 因為硬罰則（n_symbols=5 < 10）被扣了 10 分變成 -7.627。

**Session 1 驗證過的發現**：
- 4h 是最佳頻率：1h 太雜訊（exp4）、1D 信號太少（exp10）
- RSI(21) >> RSI(14)，對應商品 3.5 天的 supply/demand 再平衡週期
- BB 是趨勢市（W1）的關鍵保護：移除 BB 後 W1 從 2.03 崩到 0.69
- 非對稱閾值（long=35/short=75）匹配商品「結構性偏多」
- RSI 50 出場數學最優（對稱中點，無方向偏差）

**Session 1 已證偽的方向**：
- 純 trend following（EMA, Donchian, EWMAC, TSMOM）— 都 fail W2
- ER regime switching — 反而破壞價值
- Stochastic oscillator — 0% pct_positive
- Keltner Channel — ATR 帶太寬
- 1h 頻率、Multi-scale RSI、任何非對稱出場

**這組最需要顧問看的**：硬罰則 `n < 10 → -10` 對只有 5 個商品標的的研究來說是不可避免的 -10，這個評分設計合理嗎？還是應該改成「若 n 少於閾值則以組內多樣性其他指標替代」？

### 2.3 Index（autoresearch-index/）

**範圍**：15 個標的（AU200, DE40, US500, JP225 等）

**狀態**：Session 1 已收斂、15 個實驗、`knowledge_history/session_1.md` 已凍結

**當前 `strategy.py`**：`BuyAndHold_4h` — 真的就是 `return pd.Series(1.0, index=df.index)`

```
composite = 1.030
W1 = 1.379
W2 = 0.571
gap = 0.808
```

**結論很赤裸**：15 個實驗試過 EWMAC、Donchian、EMA momentum、TSMOM、ATR trailing stop、ER filter、vol spike filter、drawdown state machine、turn-of-month、BB dip buying — **全部輸給 B&H**。

**關鍵失敗模式**（knowledge 整理）：
- 指數在 2024 Jul-Dec 持續上漲（equity risk premium）
- 任何 flat 期間都會錯失 drift；daily drift ≈ +3-5 bps，只有預期 drawdown 大於 5 bps 才該 flat
- 加 short signal 在指數幾乎必死（W2 上漲 → short 觸發 pct_positive 硬罰則）
- `inverse-volatility weighting` 會放大「mostly flat」策略的輸家

**這組最需要顧問看的**：
1. 這是「2024 樣本期的特殊現象」還是「指數本來就不適合 active」？應該拉長樣本嗎（但會失去 2024 當 training、2025 當黑盒的結構）？
2. 如果 B&H 真的是最佳，那研究指數的意義是什麼？還是應該把指數從 portfolio 拿掉？

### 2.4 Test（autoresearch-test/）

純測試環境，用來驗證 `bash run.sh` 的 auto-reset loop 機制。不做真的策略研究。`CLAUDE.md` 明說會「做假實驗追加 dummy 資料」來觸發 plateau reset，確認 knowledge 歸檔和 git commit 流程正常。可以忽略。

---

## 3. 歷史與演進（讓你理解現在怎麼來的）

**三個演化階段**：

1. **v1：`autoresearch/`**（不是主線，歷史）
   - 136 個 checkpoint、ER regime switching 方向、最佳 composite 3.86
   - 但 2025 黑盒 validation 崩到 portfolio Sharpe -0.91 — 確認 overfit
   - 這段經驗促使我重新設計 loop、加入 DSR、加入 hypothesis-first 規範

2. **v2：`autoresearch-v2/`**（不是主線，歷史）
   - 17 個實驗、引入 hypothesis-first、一次跑全 63 標的
   - 發現「商品拖累整體」問題，motivate 拆三組

3. **目前：`autoresearch-{forex,commod,index}/`**
   - 同一套 loop、同一套引擎、同一套評分
   - 差別只在 `evaluate.py` 的 `SYMBOL_GROUP` 設定
   - 各自累積 knowledge，互不干擾

---

## 4. 開放問題（最想跟你討論）

### 4.1 評分系統
- **Q1**：`pct_positive < 35%` → -10 的硬罰則。合理嗎？商品組 pct_positive = 60% 但因為 n=5<10 一樣被扣。有沒有更符合實務的跨標的穩健性指標？
- **Q2**：`composite = mean(W1, W2)` 單純取平均是否忽略了最差窗口資訊？應該用 `min(W1, W2)` 或 `mean - λ·gap` 之類的嗎？
- **Q3**：DSR 用 `n_trials = results.tsv 行數`。同個 session 內的實驗和跨 session 的實驗該一起算嗎？知識系統本意是「sessions 之間的實驗不獨立」，這會影響 DSR 計算。

### 4.2 Walk-Forward 設計
- **Q4**：只有 2 個窗口（各 3 個月）會不會 overfit 到這兩段特定 regime？是否該改成 rolling walk-forward（每月一個 fold）？
- **Q5**：2024 H1 只當 warm-up 不進評分，是不是浪費了一半資料？

### 4.3 Autoresearch Loop
- **Q6**：plateau 判定「連續 15 次沒 IMPROVED」這個 15 是拍腦袋的。要怎麼校準？
- **Q7**：knowledge.md 是 agent 自己寫的「對自己」的訊息。這套 self-reflection 會不會累積偏差（把失敗的原因歸錯、把運氣當 finding）？
- **Q8**：hypothesis-first 的規範有沒有實質拘束力？agent 可能表面上寫 hypothesis 但實際是先看了資料再編故事（p-hacking 的包裝）。你會怎麼檢查？

### 4.4 整體方向
- **Q9**：三組各自最佳策略之後要怎麼組合成 final portfolio？權重怎麼定？（目前還沒動這一步）
- **Q10**：2025 黑盒只有一次機會。什麼時候該開封？該開封前該通過哪些 sanity check？
- **Q11**：這套「假設驅動 + plateau reset + knowledge 旋進」的 loop 設計本身，你見過類似的做法嗎？有沒有 prior art 或已知的 failure mode 我可以預先防範？

---

## 5. 如何重現

若你想實際跑一次，任選一組：

```bash
cd 回測/autoresearch-commod      # 或 -forex / -index
python evaluate.py 2>&1 | head -60
```

會看到 `--- RESULTS ---` 區塊，印出 composite、W1、W2、gap、portfolio_sharpe、各 asset group breakdown、n_trials、deflated_sharpe 等。跑一次約 20-40 秒。

若要看 agent 怎麼推導新實驗，開 Claude Code 在那個目錄，給 prompt：

```
讀 CLAUDE.md、program.md、knowledge.md。
開始 autoresearch loop，從 exp {next_id} 編號。
```

agent 會按 HYPOTHESIS → IMPLEMENT → TEST → VALIDATE → RECORD 流程跑，直到 plateau。

---

## 6. 附錄：關鍵檔案對應表

| 主題 | 檔案 | 行數 |
|---|---|---|
| 評分核心 | `backtest_engine/scorer.py` | 132 |
| 回測核心 | `backtest_engine/engine.py` | 170 |
| 每組 evaluate | `autoresearch-{g}/evaluate.py` | ~330 |
| Loop 規則 | `autoresearch-{g}/program.md` | ~100 |
| Agent 守則 | `autoresearch-{g}/CLAUDE.md` | ~80 |
| 當前策略 | `autoresearch-{g}/strategy.py` | ~100 |
| 歷史實驗 | `autoresearch-{g}/results.tsv` | forex 16 / commod 43 / index 15 筆 |
| 累積知識 | `autoresearch-{g}/knowledge.md` + `knowledge_history/` | - |

**歷史資料夾（非主線，可略）**：
- `autoresearch/`：v1，v1 overfit 到 2025 黑盒的教訓來源
- `autoresearch-v2/`：v2，拆三組的 motivation 來源
- `autoresearch-test/`：測試 loop reset 機制的 sandbox
