# 文獻回顧:財經意見領袖（KOL）追蹤與輿情分析

**作者**：施博瀚（Stan Shih）
**日期**：2026-05-20
**用途**：指導教授交辦之文獻定位查核 — 確認「台灣與國外是否有人做過 KOL／輿情追蹤研究」，並回答兩個核心問題：(1) 如何追蹤 KOL 與追蹤後的應用；(2) 前人的研究方法與成效。
**範圍**：台灣本土 + 國際學術 + 業界與監管，三軸並列。

> **方法說明**：本回顧由三個平行研究分頭蒐集 — 台灣本土（臺灣博碩士論文知識加值系統 NDLTD、華藝 airiti、Google Scholar、各校論文庫）、國際學術（SSRN／NBER／arXiv／頂級期刊）、業界與監管（公司產品頁、監管機構報告、GitHub）。所有條目均為可查證之真實來源；無法逐字核對之處已於文末「驗證限制」明確標註。

---

## 〇、給老師的一頁總結

**結論一句話**：輿情／情緒對股市的影響「有人做、且做了二十年」，但本專題真正的切角 —**「中文語境下，把『個別具名 KOL』當分析單位，用 LLM 結構化成可回測的橫斷面因子，再做條件穩健性評估」**— 在台灣是空白、在國際學術是新興、在業界是刻意被丟棄的維度。

**三軸對照表**

| 面向 | 台灣本土 | 國際學術 | 業界與監管 |
|---|---|---|---|
| 研究成熟度 | 中偏低，題材偏斜 | 高度成熟、跨領域、快速演進 | 高度商用化（替代數據市場 2026 約 178 億美元） |
| 追蹤的「分析單位」 | 匿名集體輿情（整個 PTT 板／整體新聞） | 匿名社群 **＋** finfluencer 個體 | 交易行為（跟單）／匿名聚合輿情（情緒供應商） |
| 主流追蹤方法 | 詞典 → ML → BERT → LLM | 詞典 → ML → 預訓練模型 → LLM，並走向因果推論 | 規則集 → NLP／LLM |
| 追蹤後的應用 | 漲跌方向預測為主 | KOL 技術分層、策略回測、因果效果 | 跟單下單、情緒 alpha 因子、合規監控 |
| 量化成效 | 弱但顯著；極少報夏普（最佳一篇 0.759） | finfluencer 28/16/56 三分；反向策略 ~1.2%／月 | S-Score 多空 Sharpe 2.50（供應商自評） |
| 「個別具名 KOL 因子化」 | ❌ 幾乎空白 | △ finfluencer 有，但用英文＋使用者自貼標籤 | ❌ 刻意把「是誰說的」聚合掉 |
| 「條件穩健性」評估 | ❌ 無 | △ 有觀察（情緒訊號是條件性的），無系統化框架 | ❌ 無（反指標產品都做「無條件」而失敗） |

**對專題的兩個立即提醒**：
1. **可以保留的 novelty**：中文 × 具名 KOL × LLM 結構化因子 × 條件穩健性 — 這個「組合」確實空白。
2. **必須修正的措辭**：不要說「中文財經沒人做」或「LLM-as-Formatter 是全新架構」— 中文情緒 NLP 已有人做（萬鴻毅 2025）、LLM 評分轉因子的 pipeline 也已有人做（Lopez-Lira & Tang 2023）。詳見第六節缺口分析。

---

## 一、研究全景

「社群文本 → 金融市場」的研究自 2004 年 Antweiler & Frank 在《Journal of Finance》發表留言板研究起，已累積二十餘年。整個領域可分四個次主題，依與本專題的相關度排序：

1. **Finfluencer（金融網紅）個體研究** — 最新興、與本專題最直接相關。由 Kakhbod et al. (2023)《Finfluencers》引爆。
2. **社群／新聞情緒與股票報酬** — 最成熟，頂級期刊密集發表。
3. **跟單／社群交易（copy-trading）** — 行為金融取向，研究跟單者與領頭者的績效與偏誤。
4. **分析師／薦股者技術評估** — 最古典，提供「如何區分真技術與運氣」的方法論基礎。

三個跨軸的關鍵共識（對因子設計至關重要）：
- **訊息「量」幾乎總是預測成交量與波動度，但對「報酬」的預測力弱且條件化。**
- **情緒「語氣」對當期報酬正相關，但次期常反轉**（過度樂觀 → 價格回吐）。
- **「人氣」與「技術」在 finfluencer 與社群交易中呈零相關或負相關** — 絕不可用追蹤者數當品質權重。

---

## 二、台灣本土研究

### 2.1 總體判斷

台灣在「輿情／情緒 → 股市」主線上有相當數量的研究（碩士論文數十篇、期刊論文十餘篇），但**題材高度偏斜**：95% 的研究把輿情當成「匿名集體情緒池」，資料源幾乎全部押在 **PTT Stock 板**與**財經新聞**。沒有人把「股癌、游庭皓、某投顧老師」當作獨立分析單位逐人追蹤。方法演進清楚（詞典 → ML → BERT → LLM），但越新的研究回測設計反而越粗糙（多停在漲跌方向準確率）。

### 2.2 最相關的四篇（詳述）

**T1｜大數據以音訊來源之應用：各股市分析師與電視名嘴交叉分析尋找投資標的**
楊志中、謝莉醇｜2017｜SEAIT2017 第 9 屆企業架構與資訊科技研討會
- **資料**：電視財經節目（「股市現場」）名嘴語音檔 + 證交所收盤價、籌碼、新聞。
- **追蹤方法**：語音辨識轉文本 → 字串擷取做「關鍵股票文字雲」（辨識出名嘴提到的台積電、鴻海等個股）。
- **方法**：倒傳遞類神經網路（BPN）結合技術／籌碼／名嘴文本。
- **成效**：**這是一篇「研究計畫／預期成果」性質的會議論文，只完成語音轉文本與文字雲，未實際回測，無報酬或準確率數字。**
- **意義**：台灣最接近「KOL／名嘴追蹤」概念的學術文獻 — 但**前人想到了、沒做完**。可在報告中當作「本專題延續並完成此構想」的對照點。
- 出處：https://www.aea-taiwan.org/SEAIT2017/papers/030.pdf

**T2｜新聞情緒指標與臺灣加權股價指數之關係**
陳冠臻、林忠億、陳宏銘｜2021｜《人文及社會科學集刊》33(3): 383-423（中研院）
- **資料**：財經新聞文字。
- **追蹤方法**：文字探勘量化出「正向情緒變數」與「負向情緒變數」。
- **方法**：文字探勘 + 迴歸 + **含交易成本的做多策略回測**。
- **成效**：納入負向情緒的策略最佳收益率 **13.308%、夏普指標 0.759**、期末現值 197.5 萬，皆優於不含情緒的策略；**負面情緒預測力優於正面**。
- **意義**：台灣**極少數明確報告夏普值**的情緒選股研究 — 0.759 可當作「台灣情緒選股的已知績效水準」基準線，本專題回測結果應與之對比。
- 出處：https://www.rchss.sinica.edu.tw/files_news/33-03-2021/1.pdf

**T3｜利用新聞與社群貼文標題的情緒分析以預測個股股價走勢 — 以台積電為例**
萬鴻毅｜2025｜淡江大學資訊工程學系碩士班
- **資料**：2023/8–2025/3 的 PTT 股市版與鉅亨網「台積電」標題。
- **追蹤方法**：用中文 LLM 開發三種 BERT 情緒模型（EC_BERT／Dict_BERT／PN_BERT）。
- **成效**：EC_BERT 分析新聞標題最佳，**準確率最高 57.14%**；強調「微調資料須與應用場景相符」。
- **意義**：台灣**最新、與本專題最接近的「鄰居」**。務必引用 — 但要說清楚差異化：它做的是「單一標的 × 標題情緒 × 方向預測」，本專題做的是「個別 KOL × 言論結構化 × 橫斷面因子回測」。**這篇證明「中文財經情緒 NLP」已有人做，所以本專題不能宣稱該層面是空白。**
- 出處：https://www.airitilibrary.com/Article/Detail/U0002-0106202518535400

**T4｜投資人情緒與股票報酬互動關係**
周賓凰、張宇志、林美珍｜2007｜《證券市場發展季刊》20(1)
- **資料／方法**：以市場週轉率、IPO 比、資券餘額比作情緒代理變數（市場行為型，非文本型）；時間序列計量。
- **成效**：投資人情緒與「下一期」市場報酬呈**負向關係**。
- **意義**：台灣投資人情緒研究最常被引用的奠基論文。其「樂觀偏誤 → 落後一期負相關」結論，提醒本專題：KOL 看多訊號很可能是反向指標，因子設計須保留正負兩個方向假設。
- 出處：https://www.mgt.ncu.edu.tw/~choup/sentiment.pdf

### 2.3 其餘台灣文獻（彙整）

| 編號 | 題目／作者年份 | 資料源 | 方法 | 成效 |
|---|---|---|---|---|
| T5 | 新聞情緒及關注程度對台灣證券市場影響（李律昕 2022，師大管研所） | 個股新聞 + 網路搜尋量 | 文字探勘 + 迴歸 | 新聞情緒與關注度對個股報酬、流動性、機構交易行為皆顯著正向影響 |
| T6 | 情感分析對股票市場的資訊內涵 — 以 PTT 股票版為指標（陳冠淵 2019，北科大） | PTT 留言 + 財務指標 | PCA 整合五指標 | PTT 情緒預測表現優於部分傳統財務指標；與報酬呈落後一期負相關 |
| T7 | Integrating Taiwan financial BERT with CNN-BiLSTM-SA（2025，*Discover Computing*） | PTT Stock 板 + 台股新聞 | 中文 FinBERT + CNN-BiLSTM-SA | 加入社群情緒後方向預測準確率 90.62%（須留意是否含資料洩漏） |
| T8 | Social Network Sentiment + Genetic Algorithm（2023，*IJCIS*） | PTT 台積電留言 + 籌碼 | HGA 變數篩選 + LSTM | 籌碼 + 社群情緒可提升 LSTM 漲跌預測準確率 |
| T9 | 情緒指標與股價報酬關係（徐清俊、顏雯津 2008，明新學報） | VIX 等市場型指標 | VECM、衝擊反應 | 台指 VIX 領先加權指數且呈反向 |
| T10 | 透過社會大眾情緒預測台灣股市（2016，台大碩論） | PTT 等網路情緒 | 情緒分析 + 預測 | 確立「PTT 集體情緒 → 台股」研究路線 |
| T11 | 文字探勘應用於股票論壇投資議題 — PTT Stock 版（2020，北醫碩論） | PTT Stock 版 | 主題／議題探勘 | 「議題型」研究，非報酬預測 |
| T12 | 文字探勘預測企業財務舞弊 — PTT + 重大訊息（2023，中央碩論） | PTT 留言 + 重大訊息 | 文字探勘 + 分類 | **少數把 PTT 輿情用於「風險偵測」而非報酬預測** |
| T13–T14 | 財經評論文本／電子類股情緒預測（2015、2016，政大碩論） | 財經評論文本 | 情感分析 + 趨勢預測 | 「財經文本情緒 → 股市趨勢」路線 |
| T15 | 改良式資料增強 + multi-channel GRU 台股模型（廖偉成 2021，台大） | PTT 文章 + 交易資料 | 資料增強 + 多通道 GRU | 涵蓋 1600+ 股的台股交易預測模型 |

### 2.4 台灣業界產品（FinTech／券商）

| 名稱 | 機構 | 追蹤方法 | 應用 | 成效揭露 |
|---|---|---|---|---|
| 股市爆料同學會 + 籌碼K線 | CMoney（全曜財經） | 全台最大股市討論社群（月活躍逾 80 萬）；內建「**達人多空績效排行榜**」追蹤每位平台達人的勝率與推薦標的 | 散戶依達人榜跟單、依籌碼集中度選股 | 商業產品，無公開可驗證的學術級績效數據 |
| 「輿情大師」App | 宏遠證券 | 蒐集新聞、論壇、討論區，建約 600 萬筆數據模型 | 「技術／財務／籌碼／**網路聲量**」四面向選股 | 報導未提供任何績效數字 |

> **觀察**：台灣業界（CMoney 達人榜）其實已經在做「對具名達人做績效排名」— 這正是學界缺乏的「KOL 績效量化評估」雛形。但業界版本無公開方法論、無風險調整、無可驗證數據。

---

## 三、國際學術研究

### 3.1 A 組：Finfluencer（金融網紅）個體研究 — 與本專題最直接相關

**I-A1｜Finfluencers**（**本專題必引的核心基準**）
Kakhbod、Kazempour、Livdan、Schürhoff｜2023｜SSRN 工作論文（abstract_id=4428232）／CEPR DP20204
- **資料**：StockTwits 推文層級資料，涵蓋 **29,000+ 名金融網紅**。
- **追蹤方法**：辨識每位網紅對個股的多空表態 → 建構其「推薦組合」報酬序列 → 用資產定價模型估每人 alpha → 以機率性技術衡量（Bayesian 後驗 + KS 適合度檢定）分三類。
- **應用**：(1) 網紅技術評估與分類；(2) 對「反技術」網紅的建議**反向操作**。
- **成效**：**28% 有技術**（月異常報酬 +2.6%）、**16% 無技術**（雜訊）、**56% 反技術**（月異常報酬 −2.3%）。反直覺發現：反技術網紅貼文更樂觀、追蹤者更多、對散戶影響更大；發文越頻繁技術越差。對反技術網紅反向操作的策略可獲 **~1.2% 月樣本外報酬**。
- **意義**：證明「把 KOL 意見量化成因子」國際上已有先例；同時警告必須對 KOL 做**技術分層**、「反技術 KOL」本身就是反向訊號源、高人氣 ≠ 高品質。
- 出處：https://papers.ssrn.com/sol3/papers.cfm?abstract_id=4428232 ／ https://cepr.org/publications/dp20204

> **與你 PoC 的呼應**：你 PoC README 已引用此論文。你對「巴逆逆」305 筆預測的 PoC 發現「順著她做 hit rate ≈ 56%」— 這正是 Kakhbod et al. 的「反技術 KOL」型態在中文單一 KOL 上的實證複現。這是報告裡很有力的一筆。

| 編號 | 題目／發表處 | 資料與方法 | 成效 |
|---|---|---|---|
| I-A2 | Finfluencer Recommendations（*Economics Letters* 2025） | 網紅薦股事件研究 + 橫斷面迴歸 | 網紅傾向推薦「過去強、量大、估值高」的熱門股；**推薦「數量」可預測未來報酬** |
| I-A3 | VideoConviction（arXiv:2507.08104, 2025） | YouTube 網紅影片多模態基準（影像+語音+文字） | **績效差的網紅常以更高「信念強度」呈現建議**；高信念+高正面情緒令散戶採納劣質建議 |
| I-A4 | Finfluencers & IPO Valuations（*J. of Behavioral Finance* 2025） | 395 檔印度 IPO + 網紅貼文，橫斷面迴歸 | 有網紅背書的 IPO 折價與初期報酬顯著更高（顯著性偏誤、羊群行為） |

### 3.2 B 組：社群／新聞情緒與股票報酬

| 編號 | 題目／作者年份／發表處 | 資料與追蹤方法 | 成效結論 |
|---|---|---|---|
| I-B1 | Antweiler & Frank (2004)，*J. of Finance* | Yahoo!／Raging Bull 留言板 150 萬則訊息；計算語言學分類看多／看空 | **奠基之作**：訊息可預測波動度；對報酬「統計顯著但經濟意義微小」；分歧度與成交量相關 |
| I-B2 | Tetlock (2007)，*J. of Finance* | 《華爾街日報》專欄；Harvard-IV 詞典量化「悲觀度」 | 高媒體悲觀度預測**短期下跌後回歸基本面**；確立「語氣 → 當期正向、次期反轉」經典模式 |
| I-B3 | Bollen, Mao, Zeng (2011)，*J. of Computational Science* | 2008 Twitter；OpinionFinder + GPOMS 情緒；SOFNN 預測 | 宣稱「Calm」情緒 Granger-導致 DJIA、準確率 86.7% — **但後續遭 Lachanski & Pav (2017) 嚴重批評，結果無法重現** |
| I-B4 | Bartov, Faurel, Mohanram (2018)，*The Accounting Review* | 99.8 萬則財報前推文；彙總個人投資者情緒 | 群眾推文可預測次季盈餘與公告報酬；**準確度高於分析師** |
| I-B5 | Chen, De, Hu, Hwang (2014)，*Review of Financial Studies* | Seeking Alpha 文章與留言的語氣分析 | 語氣**負向**預測未來三月報酬；多空虛擬策略多年累積約 40%；預測力超越賣方研究 |
| I-B6 | Divernois & Filipović (2024)，*Digital Finance* | StockTwits 訊息分類，建「極性」指標 | 極性與當期報酬正相關但**無法預測次日報酬**；**唯有「訊息量暴增事件」時極性才有預測力** |
| I-B7 | Cookson & Niessner (2020)，*J. of Finance* | StockTwits 社群網路；建「分歧度」指標 | 分歧度穩健預測異常成交量（跨群分歧 +1 標準差 → 次日異常量 +4%） |
| I-B8 | Cookson, Engelberg, Mullins (2023)，*Review of Financial Studies* | StockTwits 追蹤者網路；衡量資訊「同溫層」程度 | 投資者主動進入同溫層、信念兩極化 |
| I-B9/B10 | GameStop 研究（*Economics Letters* 2022／*JBEF* 2021） | r/WallStreetBets 貼文、Twitter 數；事件期計量、小波分析 | Reddit 活動對 GME 異常報酬顯著正向；2021/1 暴漲**主要由社群情緒而非基本面驅動** |
| I-B11 | Araci (2019) FinBERT，arXiv:1908.10063 | BERT + 金融語料微調 | 超越當時 SOTA 傳統 ML — 標誌方法從詞典／ML 轉向預訓練語言模型 |
| I-B12 | Lopez-Lira & Tang (2023)，SSRN 4412788／arXiv:2304.07619 | 5 萬+ 新聞標題；**ChatGPT/GPT-4 zero-shot 評分 → 多空策略回測** | GPT-4 命中初始反應 ~90%；ChatGPT 分數顯著預測漂移；策略成本前日均 ~38bp、累積逾 650% |

> **I-B12 對本專題方法論最具參考價值**：它示範了「LLM zero-shot 評分 → 量化因子 → 嚴謹回測（含資料洩漏防範、交易成本、樣本外）」的完整 pipeline。**這也意味本專題的「LLM-as-Formatter」不能宣稱是全新架構** — 詳見第六節。
> **I-B3 是反面教材**：高準確率宣稱必須有嚴謹樣本外驗證。本專題回測務必避免此覆轍。

### 3.3 C 組：跟單／社群交易研究

| 編號 | 題目／作者年份／發表處 | 資料與方法 | 成效結論 |
|---|---|---|---|
| I-C1 | Apesteguia, Oechssler, Weidenholzer (2020)，*Management Science* | 受控實驗室實驗 | 提供「他人成功資訊」顯著增加風險承擔；可直接複製時增幅更大 → 跟單**可能導致過度冒險、降低福利** |
| I-C2 | Pelster & Hofmann (2018)，*J. of Banking & Finance* | 社群交易平台個人交易紀錄；DiD | 成為「被跟隨領頭者」**顯著增強處置效應**（聲譽損失恐懼） |
| I-C3 | Heimer (2016)，*Review of Financial Studies* | 投資社群網路；自然實驗 | 接觸社群網路使處置效應**幾乎翻倍** |
| I-C4 | To Follow or Not to Follow（*QREF* 2018） | 社群交易平台領頭者／跟隨者報酬 | 高活躍交易與報酬負相關；**不存在「群眾智慧」效應 — 追蹤者數與報酬無正相關** |
| I-C5 | Competition for Visibility（*IRFA* 2021 等） | ZuluTrade 領頭者交易紀錄 | 績效「很好」與「很差」的領頭者都增加賭博型交易 — 排行榜誘發行為扭曲 |
| I-C6 | Community-Based Signals in Copy Trading（*JBEE* 2022） | 跟單情境行為實驗 | 跟單者選領頭者時「資歷／可信度」比績效、風險訊號更重要 |

### 3.4 D 組：分析師／薦股者技術評估（方法論背景）

| 編號 | 題目／作者年份／發表處 | 方法 | 成效結論 |
|---|---|---|---|
| I-D1 | Metrick (1999)，*J. of Finance* | 153 份投資電子報推薦組合績效評估 | **未發現投資電子報具顯著選股能力** — 古典「薦股者技術評估」框架源頭 |
| I-D2 | Loh & Stulz (2011)，NBER w14971／*RFS* | 分析師推薦變更的事件研究 | **只有少數推薦具影響力**（明星分析師、伴隨盈餘修正、不確定時期） |
| I-D3 | Frequency of Analyst Recommendation Changes（*JBF* 2011） | 依推薦修正頻率分組做組合排序 | 頻繁修正者績效優於不常修正者 — **但注意：finfluencer 中發文頻率反而與技術負相關**，方向依群體而異 |

---

## 四、業界與監管

### 4.1 總體判斷

把「人的言論／行為」轉成「可交易訊號」這件事，業界早已商用，且分裂成兩個幾乎不重疊的市場：

- **B2C 跟單市場**：追蹤對象是「交易領袖本身的下單行為」，用戶直接鏡像複製。代表：eToro、ZuluTrade、Collective2、Myfxbook、NAGA、Covesting。
- **B2B 輿情情緒數據市場**：追蹤對象是「整體匿名輿論場」（新聞 + 社群文字），產出標準化情緒分數賣給法人。代表：RavenPack、LSEG MarketPsych、Context Analytics（原 Social Market Analytics）、Bloomberg、Accern、Sentifi。

市場規模：替代數據市場 2026 年約 178 億美元，預估 CAGR 51.9% 至 2031 年 1,439 億美元（Mordor Intelligence）。RavenPack 宣稱前段班量化基金 >70% 使用其新聞分析。

### 4.2 跟單／社群交易平台

| 平台 | 追蹤方法 | 應用與成效 |
|---|---|---|
| **eToro CopyTrader** | 每位 Popular Investor 公開檔案：歷史報酬、風險分數（1–7）、最大回撤、即時持倉；下單後跟單者帳戶 ~1 秒鏡像 | Popular Investor 分四級，Elite 級可獲所管資產 1.5% 報酬；風控門檻：風險分數 <7、回撤 <30% |
| **ZuluTrade（ZuluRank）** | 專有演算法綜合成熟度、曝險、回撤、可靠度、交易頻率排名 | 平台**公開承認排名含「volume factor」**（因平台靠交易量抽成）；細節不揭露 |
| **Collective2** | 為策略領袖編公開 track record；提供獨立帳戶驗證 | **計算累積報酬時扣除典型跟單者實際成本**（訂閱費、佣金）— 業界少見的誠實做法 |
| **Myfxbook AutoTrade** | 訊號商須提供真實帳戶且至少 3 個月交易史 | 以「真實帳戶驗證」為信任機制 |
| **Covesting（PrimeXBT）** | 透明排行榜按 ROI 排名 | 每月發布 Copy Trading Report，但公布的多為極端值（某交易者 2,300% ROI）— 行銷選擇偏差 |

> **觀察**：所有平台追蹤的都是「交易行為（下單）」，**沒有一家追蹤「言論」**。且各家坦承排名有商業偏差（ZuluTrade）或不揭露。

### 4.3 輿情／社群情緒數據供應商

| 供應商 | 追蹤方法 | 應用與公開成效 |
|---|---|---|
| **RavenPack**（現整合 Bigdata.com） | 自 2003 年起從 40,000+ 來源擷取文字；「數百萬條規則集」+ ML；辨識 1,200 萬+ 實體 | 量化基金 alpha 生成；宣稱前段班量化基金 >70% 採用 |
| **LSEG MarketPsych** | 專利 NLP + **LLM** 引擎，每日處理 200 萬+ 篇文章與貼文，13 種語言 | 涵蓋 12 萬家公司；2020 年與 Refinitiv 推出「首個基於媒體情緒的選股模型」 |
| **Context Analytics（原 SMA）** | 三階段管線：擷取 Twitter/X 與 StockTwits → 驗證帳號真實性 → 產出標準化 **S-Score**（−4.25～+4.25） | **業界唯一公開完整可量化回測**：股票多空 Sharpe **2.50**、年化 25.44%；ETF 五分位差年化 >9% |
| **StockTwits（官方情緒）** | 0–100 計量分數，7 天滾動計算多空訊息百分比 | 平台內供散戶當補充指標；也是其他供應商的原始資料來源 |
| **Bloomberg** | 整合 Twitter/StockTwits feed；人工標註 → ML → 輸出 −1～+1 情緒分數 | Social Velocity 異常量警示、Event-Driven Feeds |
| **Accern／Sentifi** | 從數億網站／推文擷取，每篇衍生 60+ 分析 | 無程式碼 NLP 平台；公開量化回測有限 |

> **觀察**：(1) 方法論演進清楚：RavenPack 早期靠規則集，2020 年後全業界轉 LLM/NLP。(2) Context Analytics 的 S-Score Sharpe 2.50 是業界少數公開的成效數據，可當回測對照基準（但須註明供應商自評、有選擇偏差）。(3) **所有供應商都把成千上萬發言者「匿名聚合」成一個分數，刻意丟掉「是誰說的」維度** — 這正是本專題的差異化空間。

### 4.4 監管機構報告

| 機構／報告 | 對 KOL 影響力的量化數據 |
|---|---|
| **FINRA Foundation《社群媒體投資者特徵、行為與結果》（2026/04）** | **本回顧最有引用價值的監管量化數據**：被詐騙鎖定者中，**finfluencer 跟隨者 69% 損失金錢 vs. 非使用者 26%**（損失率超過兩倍）；社群投資者客觀知識測驗僅 42 分卻 63% 自評知識高；30 歲以下 35% 倚賴社群媒體投資 |
| **FINRA《Social Media-Influenced Investing》報告（2025/12）** | 引用 FINRA Foundation：45% 投資者從網路取得理財建議、24% 從社群媒體；明指「業界正在開發追蹤熱門持股、利用社群驅動趨勢的產品」 |
| **SEC 執法（2024–2025）** | M1 Finance 罰 85 萬美元、TradeZero 罰 25 萬美元（未監督 finfluencer）；2025/5 一券商因未監督「400+ 名社群網紅」罰 160 萬美元 |
| **FCA（英國）跨國打擊（2024–2026）** | 識別 1,267 則非法金融廣告、觸及至少 230 萬個英國帳戶；一家被網紅推廣的券商讓 9 萬名散戶 CFD 損失 7,500 萬英鎊 |
| **ASIC（澳洲）INFO 269（2022）** | 發布後「觀察到非授權 finfluencer 鼓吹金融產品的貼文明顯減少」 |
| **IOSCO 報告 FR/06/2025** | 把 copy/social/mirror trading 並列為「線上模仿交易」；指出「即使領袖獲利，跟單者仍可能因執行時差與滑價虧損」 |
| **台灣金管會 +投信投顧公會「網紅行銷自律規範」（2024/09）** | 規範「業者聘用網紅做合規行銷」；違反投信投顧法可罰 60 萬–300 萬新台幣。**注意：完全沒有觸及「把 KOL 言論當量化訊號研究」** |

> **觀察**：監管已用量化方法證明「KOL 對散戶有大規模、可測量的影響」。監管把這當「需保護散戶的風險」，沒有人把它當「值得結構化追蹤的 alpha／風險訊號」 — **本專題等於把監管已證實的事實，轉成量化研究的起點。台灣的監管也未對「KOL 言論量化研究」設限，純研究無監管障礙。**

### 4.5 開源工具

| 專案 | 內容 | 與本專題關係 |
|---|---|---|
| **banini-tracker**（GitHub, cablate／hansai-art） | 追蹤台灣財經 KOL「巴逆逆（8zz）」；Apify 爬 FB → Whisper 轉錄 → Claude/LLM 辨識標的 → FinMind 抓價；**反向訊號邏輯**；回測 2024/04–2026/04 共 2,249 則貼文、345 個明確預測，SQLite 公開 | **與本專題最直接相關的開源先例** — 但方法論弱：「成功」定義寬鬆、無交易成本、無 walk-forward |
| **8zz-Contrarian-Indicator-TradingView** | 把「巴逆逆」操作以反向訊號畫在 K 線圖 | 宣稱「勝率 81.5%」— 但為樣本選擇後自評、無獨立驗證 |
| **Tuttle SJIM（Inverse Cramer ETF）** | 商用 ETF，做空 Jim Cramer 推薦標的 | **2023/3 上市、2024/2 清算**：期間下跌 15%，同期 S&P 500 漲 25% — 證明「無條件反指標」行不通 |
| signal-tracker／FinBERT／FinGPT 類 | 通用預測追蹤框架、金融情緒模型 | 基礎建設成熟可用，但「具名 KOL → 嚴謹量化因子」這條鏈開源界只有玩票專案 |

---

## 五、回答老師的兩個核心問題

### 問題一：如何追蹤 KOL／輿情？追蹤後拿來做什麼？

**追蹤方法可分三種「分析單位」**：

1. **匿名集體輿情**（台灣學術主流、B2B 情緒供應商）：把整個論壇／所有發言者聚合成一個情緒分數。方法是文字探勘 → 詞典／ML／BERT／LLM。應用：情緒指數、漲跌方向預測、選股因子。
2. **交易行為**（B2C 跟單平台）：追蹤交易領袖的實際下單，轉成標準化績效指標（報酬、回撤、勝率、風險分數）做排行榜。應用：自動鏡像下單（跟單）。
3. **具名個體言論**（國際 finfluencer 學術研究、banini-tracker）：把特定一個有名有姓的 KOL 當分析單位，辨識其每則表態。方法：StockTwits 自貼標籤（學術）或 LLM 抽取（banini-tracker）。應用：KOL 技術分層、反向操作策略、績效評估。

**追蹤後的應用**橫跨：跟單下單、績效評估排行、情緒 alpha 因子、漲跌預測、風險偵測（財務舞弊早期警訊）、合規監控（監管機構）。

### 問題二：前人的研究方法與成效

**研究方法演進三階段**：

| 階段 | 時期 | 代表方法 | 代表文獻 |
|---|---|---|---|
| 詞典法／計算語言學 | 2004–2011 | Harvard-IV 詞典、看多比例計數 | Antweiler & Frank (2004)、Tetlock (2007) |
| 機器學習／預訓練模型 | 2014–2022 | SVM、隨機森林、BERT 領域微調（FinBERT） | Chen et al. (2014)、Araci (2019) |
| 大型語言模型（LLM） | 2023– | GPT-4 zero-shot 評分、多模態 | Lopez-Lira & Tang (2023)、VideoConviction (2025) |

研究設計也從「相關」走向「因果」（DiD、自然實驗）再走向「可交易性」（嚴格防資料洩漏、計交易成本、樣本外）。

**成效**（依嚴謹度排序）：
- **嚴謹回測有量化 alpha 者**：Lopez-Lira & Tang (2023) 策略累積逾 650%；Kakhbod et al. (2023) 反向策略 ~1.2%／月；Context Analytics S-Score Sharpe 2.50（業界自評）。
- **台灣本土**：陳冠臻等 (2021) 夏普 0.759、收益率 13.3% — 台灣唯一明確報夏普者。多數台灣研究只報方向準確率（57%–90%）。
- **跟單交易**：學術一致發現「人氣 ≠ 績效」、跟單增加過度冒險。
- **反指標商用嘗試全部失敗或無嚴謹驗證**：SJIM 清算、banini-tracker 過度宣稱。
- **反面教材**：Bollen et al. (2011) 的 86.7% 準確率無法重現。

---

## 六、缺口分析 — 對照你的 KOL 專題 v4

> 本節對照 `docs/評審簡報_KOL量化平台_v4.md`，逐一查核 v4 的關鍵主張在文獻基礎上是否站得住。**走校準路線，不吹捧。**

### 6.1 v4 主張的查核裁決

| v4 的主張 | 文獻查核結果 | 裁決 | 建議 |
|---|---|---|---|
| 「中文財經 KOL 結構化資料空白」（Slide 4 C1） | 大致成立 — 台灣全部把輿情當匿名聚合，無人以「具名個別 KOL」為分析單位 | ✅ **站得住** | 保留，但措辭精確化（見 6.2） |
| 「英文社群量化研究不適用中文市場，中文財經缺少對等方法論與資料集」（Slide 2） | **部分成立** — 中文財經情緒 NLP 已有人做（萬鴻毅 2025、Taiwan FinBERT 2025、社群+LSTM 2023） | ⚠️ **需修正** | 不是「中文沒人做情緒 NLP」，是「中文沒人做**具名 KOL 因子化**」 |
| C2「LLM-as-Formatter 是 LLM × 金融研究中少見的設計選擇」 | **需修正** — Lopez-Lira & Tang (2023) 已做「LLM zero-shot 評分 → 因子 → 回測」 | ⚠️ **需修正** | 改為「相對 Lopez-Lira & Tang 的差異是**職責分離**」（見 6.3） |
| Slide 2 刪除 banini-tracker 對照列 | **不建議刪** — banini-tracker 是最直接的開源先例，已回測 2,249 則貼文，老師若 google 必然找到 | ❌ **建議改回** | 加回並用其方法論弱點凸顯你的嚴謹度（見 6.4） |
| 「條件穩健性／多情境壓力測試」（核心方法） | **強烈成立** — SJIM 失敗、Divernois & Filipović (2024) 已證明情緒訊號預測力是條件性的，但無人系統化 | ✅✅ **最硬的 novelty** | 保留並強化，當作報告主賣點（見 6.5） |
| 「KOL 比散戶早解讀公開資訊」資訊擴散假說（Slide 3） | 文獻無直接驗證，但 Bartov et al. (2018) 顯示群眾推文可預測盈餘 | ✅ 合理可驗證 | 保留，定位為「待驗證假說」即可 |

### 6.2 真正站得住的 novelty

文獻交叉比對後，本專題**真正空白的交集**是：

> **「中文語境 × 以『個別具名 KOL』為分析單位 × 用 LLM 結構化成橫斷面可回測因子 × 條件穩健性／壓力情境評估」**

每個單一元件在某處都已存在 —
- 中文情緒 NLP：萬鴻毅 (2025)、Taiwan FinBERT (2025) — **已存在**
- 具名個別 KOL：Kakhbod et al. (2023) — **已存在**，但用英文 + StockTwits 使用者自貼標籤（非 LLM 抽取自由文本）
- LLM 結構化成因子：Lopez-Lira & Tang (2023) — **已存在**，但對象是英文新聞標題、非 KOL
- 條件穩健性：Divernois & Filipović (2024) 觀察到情緒訊號的條件性 — **作為觀察存在**，但無人把它做成系統化的壓力測試框架
- 跟單／反指標：banini-tracker、SJIM — **已存在**，但無嚴謹回測

**所以你的 personal contribution 必須定位在「組合」與「方法論嚴謹度」，不是任何單一元件。** 這是誠實且仍然站得住的定位。

### 6.3 LLM-as-Formatter 的措辭修正

v4 Slide 4 C2 寫「在 LLM × 金融研究中，多數直接用 LLM 輸出 confidence；本研究選擇分離職責」。
**問題**：Lopez-Lira & Tang (2023) 確實直接用 LLM 評分，但它本身就是一個高度可回測、嚴謹的研究 — 不能把「直接用 LLM」一概說成缺點。
**建議改法**：把 C2 定位成「相對於 Lopez-Lira & Tang (2023) 直接用 LLM 分數當訊號，本研究**把方向抽取與權重評分拆開** — LLM 只做方向，權重由 KOL 歷史 WFE 外部決定。此設計的動機是避免 LLM 自評 confidence 不可校準的已知問題。」這樣引用了基準、講清楚差異、也不過度宣稱。

### 6.4 banini-tracker：建議「正面對決」而非刪除

v4 在 4/24 修訂時刪掉了 banini-tracker 對照列。但業界調查顯示它是**最直接的開源先例**：同樣用 LLM 結構化單一中文財經 KOL（巧的是也是「巴逆逆」，與你 PoC 同一人）、回測 2,249 則貼文。
**建議**：把它加回 Slide 2 或 Q&A，並主動指出它的方法論弱點正是你的貢獻所在 —
- banini-tracker 把「巴逆逆」當**永遠的反指標**（無條件）→ 你做**條件性**評估（她在什麼情境下才反向）。
- 「81.5% 勝率」是樣本選擇後自評、無交易成本、無 walk-forward → 你做嚴謹的、含成本的、out-of-sample 回測。
- 單一 KOL → 你做多 KOL 橫斷面分層。
**理由**：老師若自己 google「巴逆逆 量化」一定找到它。主動處理 + 用它墊高你的嚴謹度，遠比被問倒好。

### 6.5 條件穩健性 — 你最硬的賣點，建議加碼

這是文獻查核中**唯一同時通過「學術空白」與「業界反覆失敗」雙重驗證**的點：
- SJIM（Inverse Cramer ETF）失敗，根本原因是「無條件反指標」 — 它沒問「Cramer 在什麼市場情境下才該被反向」。
- banini-tracker 同樣把 KOL 當無條件反指標。
- Divernois & Filipović (2024) 已用 StockTwits 證明「情緒訊號的預測力條件於注意力／成交量事件」 — 但只是觀察，沒有人把它做成系統化的「KOL 因子條件穩健性評分」。

**建議**：報告中明確把這句話當主張 —「現有 KOL／反指標研究與商用產品（SJIM、banini-tracker）失敗的共同原因，是缺乏『此 KOL 訊號在何種市場情境下有效／失效』的條件分析。本研究以多情境壓力測試系統化評估 KOL 因子的條件穩健性，正是填補此縫隙。」這句話有 SJIM 失敗案例 + Divernois & Filipović 文獻雙重支撐，最硬。

### 6.6 文獻給的因子設計警訊（直接影響你的實作）

1. **絕不可用追蹤者數當品質權重** — 「人氣 ≠ 技術」是 Kakhbod et al.、To-Follow-or-Not、ZuluTrade 研究的共同結論。你 v4 用 WFE 當權重，方向正確，繼續保持。
2. **同時設計正向與反向因子** — 情緒語氣的次期反轉是反覆規律（Tetlock、Chen et al.、Kakhbod et al.）。你 PoC 已發現「巴逆逆順著做才有 edge」，與此一致。
3. **同溫層 → KOL 不是獨立樣本**（Cookson et al. 2023）。多 KOL 聚合時須做去相關／多元性校正，否則高估「群眾智慧」。
4. **回測務必防 Bollen (2011) 覆轍**：樣本外、walk-forward、交易成本、可重現性 — 直接借鏡 Lopez-Lira & Tang 的防資料洩漏設計。

---

## 七、可查證來源彙整

### 台灣本土
- 周賓凰等 (2007) 投資人情緒與股票報酬：https://www.mgt.ncu.edu.tw/~choup/sentiment.pdf
- 陳冠臻等 (2021) 新聞情緒指標（中研院全文）：https://www.rchss.sinica.edu.tw/files_news/33-03-2021/1.pdf
- 楊志中、謝莉醇 (2017) 電視名嘴交叉分析：https://www.aea-taiwan.org/SEAIT2017/papers/030.pdf
- 萬鴻毅 (2025) LLM/BERT 台積電情緒：https://www.airitilibrary.com/Article/Detail/U0002-0106202518535400
- 李律昕 (2022) 新聞情緒 + 關注度：https://www.airitilibrary.com/Article/Detail/U0021-NTNU41487
- 陳冠淵 (2019) PTT 情感分析：https://ndltd.ncl.edu.tw/handle/x3455x
- Taiwan FinBERT + CNN-BiLSTM (2025)：https://link.springer.com/article/10.1007/s10791-025-09515-3
- 社群情緒 + LSTM 台積電 (2023)：https://link.springer.com/article/10.1007/s44196-023-00276-9
- CMoney 股市爆料同學會達人榜：https://www.cmoney.tw/forum/popular/member
- 宏遠證券「輿情大師」App：https://www.ctwant.com/article/37620

### 國際學術
- Kakhbod et al. (2023) Finfluencers：https://papers.ssrn.com/sol3/papers.cfm?abstract_id=4428232 ／ https://cepr.org/publications/dp20204
- Lopez-Lira & Tang (2023) Can ChatGPT Forecast Stock Prices：https://papers.ssrn.com/sol3/papers.cfm?abstract_id=4412788 ／ https://arxiv.org/abs/2304.07619
- Antweiler & Frank (2004)：https://onlinelibrary.wiley.com/doi/abs/10.1111/j.1540-6261.2004.00662.x
- Tetlock (2007)：https://onlinelibrary.wiley.com/doi/10.1111/j.1540-6261.2007.01232.x
- Bollen et al. (2011)：https://arxiv.org/abs/1010.3003 ／ 批評：https://econjwatch.org/articles/shy-of-the-character-limit-twitter-mood-predicts-the-stock-market-revisited
- Bartov et al. (2018)：https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2782236
- Chen et al. (2014) Wisdom of Crowds / Seeking Alpha：https://www.researchgate.net/publication/228280089
- Divernois & Filipović (2024) StockTwits Sentiment：https://link.springer.com/article/10.1007/s42521-023-00102-z
- Cookson & Niessner (2020) Investor Disagreement：https://papers.ssrn.com/sol3/papers.cfm?abstract_id=4529594
- Cookson et al. (2023) Echo Chambers：https://rady.ucsd.edu/faculty/directory/engelberg/pub/portfolios/ECHO_CHAMBERS.pdf
- Araci (2019) FinBERT：https://arxiv.org/abs/1908.10063
- VideoConviction (2025)：https://arxiv.org/html/2507.08104v1
- Apesteguia et al. (2020) Copy Trading：https://pubsonline.informs.org/doi/abs/10.1287/mnsc.2019.3508
- Pelster & Hofmann (2018)：https://papers.ssrn.com/sol3/papers.cfm?abstract_id=3057533
- Heimer (2016) Peer Pressure：https://academic.oup.com/rfs/article-abstract/29/11/3177/2583763
- Loh & Stulz (2009) NBER w14971：https://www.nber.org/system/files/working_papers/w14971/w14971.pdf

### 業界與監管
- RavenPack / Bigdata.com：https://www.ravenpack.com/products/edge/data/news-analytics
- LSEG MarketPsych Analytics：https://www.lseg.com/en/data-analytics/financial-data/analytics/marketpsych-analytics
- Context Analytics S-Score 績效：https://www.contextanalytics-ai.com/performance-benchmarks/stocktwits-s-score-quintiles/
- eToro CopyTrader：https://www.etoro.com/copytrader/
- FINRA《Social Media-Influenced Investing》報告：https://www.finra.org/sites/default/files/2025-12/2025-social-media-influenced-investing.pdf
- FINRA Foundation 2026 研究：https://www.finra.org/media-center/newsreleases/2026/finra-foundation-research-examines-characteristics-behaviors-outcomes
- FCA 跨國打擊：https://www.fca.org.uk/news/press-releases/fca-leads-international-crackdown-illegal-finfluencers
- IOSCO FR/06/2025：https://www.iosco.org/library/pubdocs/pdf/IOSCOPD793.pdf
- banini-tracker：https://github.com/cablate/banini-tracker

---

## 八、驗證限制

- **NDLTD 碩博士論文**（T6、T10–T14 等）：論文詳細頁有驗證碼保護，僅能確認題目、年份、機構、論文代碼（均為真實題錄），完整摘要與量化細節需作者本人登入 NDLTD／華藝逐篇調閱補齊。
- **Kakhbod et al. (2023)**：SSRN 頁面遭 403 阻擋，方法細節綜合自 CEPR 與 QuantPedia 解析，定稿引用前應以 SSRN 原文最新版本為準。
- **FINRA／SEC／IOSCO 官方 PDF**：直接抓取時被伺服器以 403 阻擋，內容透過官方頁面與多個二手來源（ThinkAdvisor、A&O Shearman 等）交叉確認；引用一手 PDF 前建議手動下載核對。
- **banini-tracker「81.5% 勝率」「2,249 則貼文」**：數字來自專案 README 自述，非獨立驗證，引用時應標明。

---

## 九、後續建議

1. **定稿前補齊全文**：登入師大圖書館資料庫／NDLTD，逐篇調閱 T6、T10–T14 的全文，核對指導教授與量化細節。
2. **更新提案 v4**：依第六節 6.2–6.5，修正三處措辭、加回 banini-tracker 對決、強化條件穩健性主賣點 → 產出 v5。
3. **必引清單**：報告「現有研究」一節至少引用 Kakhbod et al. (2023)、Lopez-Lira & Tang (2023)、萬鴻毅 (2025)、Divernois & Filipović (2024)、楊志中與謝莉醇 (2017)、陳冠臻等 (2021)。
