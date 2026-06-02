# v5 補充段落:C4(Anti-Survivorship)+ Lookahead Bias 控制

**作者**:施博瀚
**日期**:2026-05-27
**用途**:供 v5 簡報整合使用的兩個新段落 + 三題 Q&A 防禦
**配套**:
- [docs/西方文獻比較_2026-05-27.md](西方文獻比較_2026-05-27.md)(完整論述)
- [docs/評審簡報_KOL量化平台_v4.md](評審簡報_KOL量化平台_v4.md)(現有簡報)

---

## 整合位置建議

| 新內容 | 對應的 v4 位置 | 建議整合方式 |
|---|---|---|
| **§A. C4 Contribution** | Slide 4(我的貢獻) | 在 C3 之後加 C4,並更新「三者的關係」為「四者的關係」 |
| **§B. Lookahead Bias 控制** | Slide 6(進度與風險) | 在「主要風險與緩解」表格之後新增獨立小節 |
| **§C. Q7-Q9 Q&A** | 部分 D Q&A | 直接附在 Q6 之後 |

---

## §A. 新 Contribution 4 段落(放 Slide 4)

### Contribution 4(方法論面):全集 KOL 池 × WFE 唯一篩選框架(Anti-Survivorship Selection)

**問題定位**:現有 finfluencer 量化研究在 KOL 入池上普遍存在 survivorship bias——

| 對位研究 | 篩選方式 | bias 性質 |
|---|---|---|
| Kakhbod et al.(2023)Finfluencers | StockTwits 自貼標籤的 finfluencer | **自我選擇偏差**(願意公開立場才入庫) |
| VideoConviction(KDD 2025) | 手動挑 22 個 YouTube,標準:follower count + content frequency | **倖存者偏差**(只挑紅的) |
| Hull & Qi(2024 Nordic) | 社交交易平台上的 finfluencer | **平台預篩偏差** |
| banini-tracker / SJIM | 只盯一個 KOL(巴逆逆 / Cramer) | **極端 cherry-picking** |

**本研究的方法論貢獻**:可重現的「全集 KOL 池 + WFE 唯一篩選」框架——

1. **入池規則明文化**:對台灣財經 KOL 公開內容(PTT、FB、Threads、Podcast、YouTube)系統性爬取;任何滿足明文條件(月發文量 ≥ X、近 12 個月提及個股 ≥ Y 篇)的 KOL 進入候選池,**不由研究者主觀挑選**
2. **WFE-only 篩選**:候選池所有 KOL 平等跑 Walk-Forward Analysis;僅 out-of-sample WFE > 0.5 才進入下游因子化;**不看 follower 數、不看名氣、不看編輯偏好**
3. **全分佈報告**:報告整個候選池的 WFE 分佈(中位數、四分位、未通過閾值數量),讓 reviewer 驗證**未挑好故事**
4. **時光機嚴格性**:篩選決策只用 train period 末端之前的資訊;門檻值先驗決定不回頭調整

**為什麼這是真正的差異化**:
- 與西方研究的差異是**方法論層級**(不是僅資料源差異),學術上有正式名稱:**anti-survivorship bias selection**
- Lopez de Prado《Advances in Financial Machine Learning》Chapter 3 專門指出 survivorship bias 是量化研究最被低估的問題
- 雖然本研究「全集 KOL 池」規模(預期 50-200)遠小於 Kakhbod(29k+),但**未經研究者主觀篩選**的小池子對 KOL skill 異質性研究更有效——大池子若是平台預篩,結論仍受 bias 污染

**四個 Contributions 的關係(更新版)**:
> C1(schema)定義**抽什麼**;C2(LLM-as-Formatter)解決**怎麼抽**;C3(WFA 校準)決定**KOL 權重多少**;**C4(Anti-survivorship pool)解決哪些 KOL 進入分析的根本問題**。四者構成完整且互鎖的方法論;**即使下游 incremental IC 不顯著,C1-C4 各自獨立具學術貢獻**。

---

## §B. Lookahead Bias 與 Memorization 控制(放 Slide 6)

### 背景

2024-2025 年三篇關鍵論文揭示 LLM-based 金融研究的根本方法論挑戰:

| 論文 | 核心發現 |
|---|---|
| Sarkar & Vafa(ICML 2025) | LLM 對訓練截止前資訊存在 lookahead bias;**prompt 與 masking 緩解均失效** |
| Lopez-Lira, Tang, Zhu(2025) | LLM 能**精準回憶**訓練截止前的歷史經濟變數、新聞、個股報酬;記憶延伸至 embedding 層 |
| He, Lv, Manela, Wu(2025)ChronoBERT | 唯一根本解:「時序一致 LLM」(訓練資料只到分析期之前的版本);ChronoBERT 已開源 |

### 對本研究的威脅評估

- **PoC 樣本期間**:2024/04 - 2026/04(巴逆逆 305 筆貼文)
- **主流 LLM 訓練截止點**:Claude Sonnet 4.5 約 2025-Q1
- **風險分佈**:前半樣本(2024/04 - 2025/Q1)在 LLM 訓練資料含括範圍內;後半樣本為乾淨樣本

### 本研究的三層緩解策略

**第一層:設計層免疫**
- LLM-as-Formatter 設計使 LLM 只負責「文字 → 結構化方向欄位」的格式化任務,**不直接預測股價或評分**
- LLM 抽出「KOL 說『看好台積』」這個事實本身不涉及未來股價
- Memorization 風險只可能透過 LLM「記得這則貼文後來股價走勢」而扭曲三類方向標籤(-1/0/+1),扭曲空間有限

**第二層:時序透明化**
- 報告中明確標示所用 LLM 模型 + 訓練截止日期
- PoC 樣本切分為「訓練截止前」/「截止後」兩子集,獨立報告:
  - 抽取一致性(direction 標籤的時序穩定性)
  - 下游 IC(兩子集的因子表現)
- **結論期望**:若兩子集結果一致 → 證明 memorization 影響有限

**第三層:WFE 外部評分作為防線**
- 即便 LLM 抽取的 direction 有 memorization 偏差,KOL 的最終權重由 out-of-sample WFA 決定
- 若某 KOL 訊號因 LLM 偏誤而系統性錯誤 → WFE 會低 → 權重會低 → 最終下游 IC 反映這點
- **系統具自我淨化機制**

### 主動承認的剩餘風險

Lopez-Lira & Tang(2025 v6)報告 ChatGPT-based sentiment alpha 從 2021Q4 Sharpe 6.54 衰退至 2024 上半 Sharpe 1.22。本研究承認 LLM-based sentiment 策略普遍存在容量衰減風險,但反駁理由:

1. **語言屏障**:繁體中文 + 台灣語境是英文主流 LLM 訓練稀疏區,資訊衰減速度慢於英文
2. **資訊源冷門**:個別 KOL identity 是相對冷門訊號源,被套利速度較慢
3. **動態權重設計**:WFE 動態評分本身就是「自我衰減偵測機制」——當 KOL 訊號被市場學會,WFE 自然下降、權重自然降低

### 可選加分實作(資源允許時)

採 He et al.(2025)開源的 ChronoBERT(HuggingFace `manelalab/chrono-bert-v1-19991231`)對訓練截止前子集做 robustness check:
- 對 100-200 筆 PoC 樣本用 ChronoBERT 重跑 LLM-as-Formatter
- 計算與 Claude 抽取結果的 inter-model F1
- **若 F1 ≥ 0.85** → 證明 memorization 對抽取階段影響有限,完成 reviewer-proof

---

## §C. Q&A 防禦補強(加在現有 Q1-Q6 之後)

### Q7:「VideoConviction(KDD 2025)跟你 schema 幾乎一樣,差在哪?」

VideoConviction(Galarnyk et al., KDD 2025)標註 22 個英文 YouTube finfluencer、288 部影片、687 推薦片段、6,000+ 標註,schema 為 ticker / action / conviction(1-3 離散)/ date / source。**他們的 F1 在 TAC(ticker+action+conviction)聯合任務僅 28.17%。** 三個本質差異:

1. **權重來源**:他們讓 MLLM 從影片畫面 + 語音直接判斷 conviction,但 28% F1 證明 MLLM 評信念強度不可靠;**本研究把 conviction 對位的 weight 外部化給 KOL 歷史 WFE**,職責分離繞開這個難題
2. **未做 Walk-Forward**:他們是 2018-2024 一次性回測;本研究主打 WFA-based 篩選 + out-of-sample 穩健性
3. **未對位現有因子**:他們未做對 Alpha101 / 5-Factor 的 incremental contribution;本研究明確量測 incremental IC

更根本的差異是 **C4 anti-survivorship pool**:他們手動挑 22 個熱門 YouTuber,有明顯選擇偏差;本研究是全集 + WFE 唯一篩選。

### Q8:「LLM-as-Formatter 已經被 Choi et al.(2025)做過了,你的差異是什麼?」

Choi et al.(2025 arXiv:2510.03195,作者群含 BlackRock、JPMorgan、Fidelity、MIT、Lopez-Lira)提出「LLM as extractor + embedding as ruler」對 S&P 100 財報電話會議跑出 3-Factor alpha -0.48%(t=-2.40, p<0.05)。我**承認 LLM-as-Formatter 並非由我發明**,而是同類設計思想的應用。三個關鍵差異:

1. **對象不同**:他們是企業官方文件(受監管、標準格式);本研究是 KOL 社群非官方文本(未監管、個人風格)
2. **規尺單位不同**:他們的規尺是「同公司去年同季」的 text-embedding-3-large cosine similarity(衡量指標漂移率);本研究的規尺是「同 KOL 歷史 out-of-sample WFE」(衡量個人可信度)
3. **訊號形態不同**:他們的訊號是「指標漂移率」(企業在隱藏什麼);本研究的訊號是「方向 × 信任權重」(KOL 的判斷該不該信)

簡言之,他們做企業意圖偵測,本研究做個人意見可信度評估,問題域與資料屬性不同。

### Q9:「LLM 的 lookahead bias / memorization 問題你怎麼處理?」

Sarkar & Vafa(ICML 2025)與 Lopez-Lira et al.(2025)證實 LLM 對訓練截止前資訊有 memorization 風險,且 **prompt 與 masking 都失效**。本研究的緩解是三層:

1. **設計層免疫**:LLM 只做格式化、不直接評分;LLM 抽出「KOL 說看好台積」這個事實本身不涉及未來股價
2. **時序透明化**:報告 PoC 樣本在 LLM 訓練截止前 / 後的分佈,並對截止後子集獨立驗證抽取一致性與下游 IC
3. **WFE 外部評分作為第二層防線**:即便抽取有偏差,KOL 最終權重由 out-of-sample WFA 決定;系統具自我淨化機制

我**承認** Lopez-Lira & Tang(2025 v6)報告主流 LLM-based sentiment alpha 從 SR 6.54 衰退至 1.22 是真實趨勢。本研究的反駁論點是:(1) 繁體中文是英文 LLM 訓練稀疏區;(2) 個別 KOL identity 是冷門訊號源;(3) WFE 動態權重本身具自我衰減偵測能力。

可選加分實作:採 He et al.(2025)開源的 ChronoBERT(時序一致 LLM)對部分樣本重跑做 robustness check。

---

## §D. 對 v4 的其他輕微措辭修訂(順手提醒)

以下是 v4 中**會被 reviewer 直接打**的措辭,1 行字可以改掉。**強烈建議一併處理**:

### 修訂 1:Slide 2 缺口表加一列

| 既有做法 | 缺口 |
|---|---|
| ...(原有) | ... |
| **VideoConviction(KDD 2025)YouTube 多模態抽取** | **英文 finfluencer + 22 個手動挑;無 WFA、無對 Alpha101 incremental IC、無 anti-survivorship 設計** |

### 修訂 2:Slide 4 C1 措辭(承認 EFSA)

**原文**:「填補中文財經 KOL 結構化資料空白」

**改為**:「中文金融 LLM 抽取已有 **EFSA(Chen et al., ACL 2024)** 對新聞事件做 12,160 筆五元組資料集;本研究對位是抽取 **KOL 對個股的方向操作意圖**,是該方向的細化而非重複,並由台灣資工同行 Lu & Huo(2025, 台大 / SMU)的 Financial NER 評估為前導參考。」

### 修訂 3:Slide 4 C2 措辭(承認 Choi 2025)

**原文**:「少見的設計選擇:在 LLM × 金融研究中,多數直接用 LLM 輸出 confidence;本研究選擇分離職責」

**改為**:「**相對於 Choi et al.(2025, arXiv:2510.03195)用 embedding similarity 當『規尺』衡量企業文件漂移**,本研究用 **KOL 歷史 WFE 當『規尺』衡量 KOL 對個股方向操作的可信度**。兩者皆採『LLM 抽取 + 外部規尺』職責分離設計;本研究是該設計從**企業官方文件**延伸到**社群非官方文本**的應用,並對位**未受監管的具名個體**而非企業整體。」

---

## §E. 整合工時估算

| 整合動作 | 工時 |
|---|---|
| §A C4 段落加入 Slide 4 | 15 分鐘 |
| §B Lookahead Bias 一節加入 Slide 6 | 15 分鐘 |
| §C Q7-Q9 加入 Q&A | 10 分鐘 |
| §D 三處措辭修訂 | 10 分鐘 |
| **總計** | **50 分鐘** |

**整合後預期效果**:
- Personal contributions 從 3 個變 4 個,差異化論述顯著增強
- Lookahead bias 議題從「v4 完全沒提的盲區」變成「主動處理的可控風險」
- C1 / C2 措辭從「會被反例打臉」變成「承認對位 + 清楚劃界」
- VideoConviction 從「沒提到的同型工作」變成「Slide 2 對照表 + Q&A 主動回應」

---

**END OF SUPPLEMENT**
