"""Render the video-lens HTML report from locally-transcribed content.

Pipes a JSON object with 10 template keys to render_report.py, which does
{{KEY}} substitution against ~/.claude/skills/video-lens/template.html.
"""
import io
import json
import subprocess
import sys
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", line_buffering=True)

VIDEO_ID = "gfhpbXob6LY"
VIDEO_URL = f"https://www.youtube.com/watch?v={VIDEO_ID}"
TITLE = "AI 2026 直播論壇｜AI成效盤點，向1%超級使用者取經"
CHANNEL = "數位時代Official"
DURATION = "2h 16m"
PUBLISHED = "Apr 17 2026"
VIEWS = "11,123 views"
META_LINE = f"{CHANNEL} · {DURATION} · {PUBLISHED} · {VIEWS} · ⚠ 本機 faster-whisper 轉錄（YouTube 無字幕）"

SUMMARY = (
    "數位時代 2026 年 4 月直播論壇，從三種視角剖析 AI 落地戰：總編輯王志仁以「下一臺為心智打造的腳踏車」為喻盤點 AI Internet 三波贏家與兩個公司內新職人案例；前 Google 臺灣董事總經理簡立峰點出臺灣因內需型產業加股市自我感覺良好，對 AI 衝擊感受滯後，強調從 work faster 進化到 work smarter 才能成為 1% 超級使用者；BCG 徐瑞廷以全球 CEO 調查與 BCG 實證案例揭示 AI 領先企業的三大差異——Top-Down 主導、聚焦價值創造的職能重塑、以及 10-20-70 法則（70% 資源在人才組織流程）。"
    "核心警告是：95% 企業的 AI 投資沒看到效益，不是工具不夠好而是缺乏端到端的職能重塑；代理式 AI 時代 B2B 採購鏈若不在名單上等於滅頂之災。三位講者共同的立場：CEO 必須親自下場，把 AI 當成組織賦能（改變原來做不到的事）而不是員工賦能（讓現有事情做更快）。"
)

TAKEAWAY = (
    "&ldquo;Cost of Inaction&rdquo; 已經大於&ldquo;行動的風險&rdquo;——不作為的代價比做錯更貴，因為 Gartner 預估三年內 90% B2B 採購將牽涉 AI 代理，不在 AI 採購候選名單上的供應商會被直接跳過。"
    "臺灣企業最大的盲點不是不懂 AI，而是 CEO 的注意力被眼前訂單占滿、沒有把 3-5 年後的職能重塑當必考題；簡立峰的具體建議是&ldquo;先給算力、先給 token fee，再看員工表現&rdquo;而不是反過來——因為等員工自學完再投資，人才可能已經跳槽。"
)

KEY_POINTS = """
<li><strong>10-20-70 法則</strong> — AI 領先企業只花 10% 資源在演算法、20% 在技術工具、<em>70% 在人才組織與流程</em>。
<p>徐瑞廷指出多數臺灣企業問錯問題：CEO 關心&ldquo;該用哪個模型&rdquo;、&ldquo;該不該上雲&rdquo;，但 BCG 統計顯示這些工具問題只佔 30%。真正的瓶頸是組織賦能、跨部門協同、員工能力重塑——這些是 CEO 層級才能推動的改造，不是技術長可以代勞的。這解釋了為什麼很多公司買了先進工具但 ROI 不如預期：<strong>R&D 工程師有頂尖工具但消極抵抗不用</strong>，因為擔心用了之後老闆會把交付週期從一個月縮成一週。</p></li>

<li><strong>Reshape vs Deploy：KPI 天花板差一個量級</strong> — 單純部署工具平均只帶 <em>10-15% KPI 提升</em>，端到端職能重塑可達 <em>30-90%</em>。
<p>徐瑞廷的具體案例：歐洲某生技公司 CEO 定下未來幾年省 10 億歐元的野心目標，BCG 幫他聚焦在商務／研發／行銷三個文件密集型職能——這三個部門的共同點是都要寫大量合規檔案。光是這三個燈塔專案就帶來快 2 億歐元價值（佔大目標 20%）。方法是 <strong>Mirror Process（映象流程）</strong>：同一個業務流程，一組走現行方式、一組用 AI 從零重新設計，3-5 個月對照驗證既能量化效益也能找出風險。</p></li>

<li><strong>Reshape 四原則：Top-Down、Zero-Base、Outcome-Driven、Focus</strong> — 不是每個部門各自發想要用 AI，而是 CEO 從結果倒推流程。
<p>Top-Down 指 CEO 必須親自訂突破性目標（不是叫部門長自己訂，因為部門長一定保守訂）。Zero-Base 是從&ldquo;如果我今天有 AI 會怎麼重新設計客服中心&rdquo;開始，不是在現行 1000 人流程上疊加 AI。Outcome-Driven 強調 KPI 要能回到<em>價值創造</em>（成本降 80%、上市時間縮短），不是&ldquo;AI 讓我寫文案變快&rdquo;這種 deploy 指標。Focus 則是一次只做一到兩個關鍵職能——因為公司是運轉中的商業機器，不可能 5 個職能同時重塑。</p></li>

<li><strong>B2B Agentic Commerce：不在 AI 採購名單 = 滅頂之災</strong> — 簡立峰引 Gartner：三年內 90% B2B 採購涉及 AI 代理，供應商若不出現在 agent 的候選清單中會被直接跳過。
<p>具體場景：買方企業啟動 AI procurement agent 後，系統自動篩選供應商、按鍵即完成 shipping 到結賬整條鏈。如果你的零元件公司沒有 <em>agentic commerce compliance</em>（資料格式、API、價格結構能被 agent 讀取比較），&ldquo;你基本上就是訂單就斷絕了&rdquo;。對臺灣的中小製造業供應商這是存在性威脅——過去靠業務關係維持訂單的模式會被結構性淘汰。</p></li>

<li><strong>Work Faster → Work Smarter：Copilot 時代結束，Agent 時代來臨</strong> — 簡立峰的翻譯：work faster 只是早點下班，沒有提升競爭力；work smarter 是做到你原來做不到的事。
<p>過去三年微軟的 Copilot 定位 AI 為助理（對等夥伴）；2026 年進到 Agentic AI 元年，AI 自主完成任務，人類角色從&ldquo;AI 幫人&rdquo;翻轉為&ldquo;人幫 AI 做不到的部分&rdquo;。簡立峰的警告：組織可能會從 AI 為中心來重新設計流程（<strong>一人獨角獸 / AI 原生企業</strong>就是極端形態）——AI 決定做什麼行銷、規劃完畢後才由人介入 AI 做不到的部分，這和目前臺灣企業&ldquo;人主導、AI 協助&rdquo;的心智模型剛好相反。</p></li>

<li><strong>臺灣認知落差：付費 AI 使用者 &lt;20%，但 50% 自認熟練</strong> — 簡立峰引臺灣去年網路調查。
<p>這個落差很危險，因為免費版和付費版的能力差距極大（GPT-4 → GPT-5 這種代差）。用免費版得到的&ldquo;熟練感&rdquo;讓人錯判自己水準。更深的結構性原因是臺灣為<strong>內需型服務業</strong>（2300 萬人市場），員工即使用 AI 提早下班老闆也感受不到營收增加，所以 AI 的使用動機天花板被鎖住。相對地，全球化企業（金融業海外服務、製造業全球採購）一旦進入 agentic commerce，天花板就打破——這也是為什麼簡立峰強調 AI 衝擊&ldquo;最終會來到臺灣，只是時間問題&rdquo;。</p></li>

<li><strong>組織賦能 &gt; 員工賦能：動機 80 分 vs 120 分</strong> — 簡立峰指員工的 AI 動機是&ldquo;把工作早點做完、做得不差&rdquo;約 80 分；但老闆要的是 120 分（做到原來做不到的事）。
<p>如果老闆等員工自發性推動 AI，只會拿到 80 分的員工賦能，永遠達不到 120 分的組織賦能。所以簡立峰對臺灣老闆的建議是<em>先給算力、先給 token fee，之後再根據員工運用情況決定下一波投資</em>——這剛好和多數臺灣老闆的保守直覺&ldquo;看員工表現再給資源&rdquo;相反。核心理由：等員工自學完再投資，優秀人才早被矽谷挖走了。</p></li>

<li><strong>乙方到甲方的人才大遷徙：FDE（Forward Deploy Engineer）</strong> — 矽谷 AI 公司大幅裁員，但被裁的優秀工程師不用擔心。
<p>王志仁與簡立峰都提到這個結構：開發產品的乙方工程師（Amazon 33,000、Oracle 27,000 裁員）會跑到甲方企業做 <em>Forward Deploy Engineer</em>——直接坐進客戶會議室，理解業務痛點、帶回來做產品。這個角色的意義是把&ldquo;最懂 AI 的人&rdquo;擴散到產業鏈下游，是市場的自然擴散。但臺灣的問題是自己的乙方（AI 產品開發公司）本來就少，甲方企業又找不到這種超級 AI 人才來帶動組織——所以組織轉型的人才瓶頸比美國更嚴重。</p></li>
"""

OUTLINE = """
<li><a class="ts" data-t="741" href="https://www.youtube.com/watch?v=gfhpbXob6LY&t=741" target="_blank" rel="noopener noreferrer">▶ 12:21</a> — <span class="outline-title">王志仁開場：AI 成效盤點的三個環節</span><span class="outline-detail">數位時代總編輯王志仁開場，定位本論壇為第二季 AI 專案焦點：四月雜誌《全球 AI 100 + 臺灣 AI 20》、五月 AI 新職人故事、六月 AI 臺灣未來商務展。</span></li>
<li><a class="ts" data-t="944" href="https://www.youtube.com/watch?v=gfhpbXob6LY&t=944" target="_blank" rel="noopener noreferrer">▶ 15:44</a> — <span class="outline-title">賈伯斯的腳踏車比喻</span><span class="outline-detail">1973 年 Scientific American 文章顯示人類加上腳踏車後能量效率世界前三，這啟發賈伯斯&ldquo;PC is a bicycle for our minds&rdquo;——AI 時代的腳踏車會是自駕車、機器人、無人機、還是 AI Agent？</span></li>
<li><a class="ts" data-t="1182" href="https://www.youtube.com/watch?v=gfhpbXob6LY&t=1182" target="_blank" rel="noopener noreferrer">▶ 19:42</a> — <span class="outline-title">Internet 三波贏家演進</span><span class="outline-detail">PC Internet（Cisco/Yahoo/Amazon）→ Mobile Internet（Apple/Google/FB）→ AI Internet（NVIDIA/Google/Tesla），每一波都重塑贏家名單。</span></li>
<li><a class="ts" data-t="1495" href="https://www.youtube.com/watch?v=gfhpbXob6LY&t=1495" target="_blank" rel="noopener noreferrer">▶ 24:55</a> — <span class="outline-title">全球 AI 100 + 臺灣 AI 20 盤點</span><span class="outline-detail">四大分類：基礎設施、個人賦能工具、企業應用、垂直領域（含國防 AI 如 Palantir/Anduril/Shield AI）。美國佔比從 70% 降到 50 出頭，百花齊放。</span></li>
<li><a class="ts" data-t="1743" href="https://www.youtube.com/watch?v=gfhpbXob6LY&t=1743" target="_blank" rel="noopener noreferrer">▶ 29:03</a> — <span class="outline-title">Hyperscaler 6000 億投資 + 同步裁員</span><span class="outline-detail">微軟/亞馬遜/Google/Meta 今年 AI 資料中心投資近 7000 億美金創紀錄，同時亞馬遜 Q4-Q1 裁 33,000 人、Oracle 裁 27,000 人——用算力換人力的結構性轉換。</span></li>
<li><a class="ts" data-t="2015" href="https://www.youtube.com/watch?v=gfhpbXob6LY&t=2015" target="_blank" rel="noopener noreferrer">▶ 33:35</a> — <span class="outline-title">AI 新職人：博源 + 韋韋山案例</span><span class="outline-detail">博源從雜誌編輯轉型 AI 簡報課程講師（銷售破百萬）；韋韋山從網站 PM 變身一天一 AI 電子報 Product Owner（三萬訂戶）——都是 Job Transformation 而非 Job Description 的範例。</span></li>
<li><a class="ts" data-t="2373" href="https://www.youtube.com/watch?v=gfhpbXob6LY&t=2373" target="_blank" rel="noopener noreferrer">▶ 39:33</a> — <span class="outline-title">簡立峰：AI 的真實能力邊界</span><span class="outline-detail">AI 三年四個月內從語言理解進步到數學 Olympiad 金牌，但在物理世界能力還不如兩歲小孩——斜坡會滾、熱水會燙這種 common sense AI 仍做不到。</span></li>
<li><a class="ts" data-t="2683" href="https://www.youtube.com/watch?v=gfhpbXob6LY&t=2683" target="_blank" rel="noopener noreferrer">▶ 44:43</a> — <span class="outline-title">Work Faster → Work Smarter</span><span class="outline-detail">從 Copilot（早點下班）進化到 Agentic AI（做原本做不到的事）。IT 一個人做十人事、行銷從發想到投放一人搞定，都是 work smarter 的具體樣貌。</span></li>
<li><a class="ts" data-t="2993" href="https://www.youtube.com/watch?v=gfhpbXob6LY&t=2993" target="_blank" rel="noopener noreferrer">▶ 49:53</a> — <span class="outline-title">Agentic Enterprise：代理型企業</span><span class="outline-detail">從管人變成管 AI 代理人，數位員工成為標配，算力和人力產生競爭——越來越多 CEO 寧可把錢投 token fee 也不增 headcount（算力 24/7、員工只 8/5）。</span></li>
<li><a class="ts" data-t="3413" href="https://www.youtube.com/watch?v=gfhpbXob6LY&t=3413" target="_blank" rel="noopener noreferrer">▶ 56:53</a> — <span class="outline-title">Q&amp;A 啟動：為何臺灣沒大裁員</span><span class="outline-detail">志仁問：美國大裁員、臺灣沒發生，為什麼？簡立峰答：臺灣內需型服務業天花板沒打破，AI 使用動機弱；付費用戶&lt;20% 但 50% 自認熟練，認知落差大。</span></li>
<li><a class="ts" data-t="3937" href="https://www.youtube.com/watch?v=gfhpbXob6LY&t=3937" target="_blank" rel="noopener noreferrer">▶ 65:37</a> — <span class="outline-title">組織賦能 &gt; 員工賦能</span><span class="outline-detail">員工動機 80 分（早點下班）vs 老闆動機 120 分（做到原來做不到的事）——自發性推動達不到老闆的目標。老闆必須親自下場。</span></li>
<li><a class="ts" data-t="4063" href="https://www.youtube.com/watch?v=gfhpbXob6LY&t=4063" target="_blank" rel="noopener noreferrer">▶ 67:43</a> — <span class="outline-title">B2B Agentic Commerce：滅頂之災</span><span class="outline-detail">Gartner 預估三年內 90% B2B 採購涉及 AI 代理，不在推薦名單的供應商&ldquo;基本上訂單就斷絕&rdquo;——這對臺灣製造業供應鏈是存在性威脅。</span></li>
<li><a class="ts" data-t="4537" href="https://www.youtube.com/watch?v=gfhpbXob6LY&t=4537" target="_blank" rel="noopener noreferrer">▶ 75:37</a> — <span class="outline-title">中小企業用 Gemma 4 即可起步</span><span class="outline-detail">Google Gemma 4 參數只有 GPT-4 的 1/20 但效果相當，一張顯示卡就能跑；臺灣中小企業不需要等算力降價才啟動。重點在軟體從工具變服務、綁住客戶的信賴感。</span></li>
<li><a class="ts" data-t="4820" href="https://www.youtube.com/watch?v=gfhpbXob6LY&t=4820" target="_blank" rel="noopener noreferrer">▶ 80:20</a> — <span class="outline-title">徐瑞廷 JT 登場：全球 CEO 調查</span><span class="outline-detail">BCG 年初調查：CEO 今年 AI 投資比去年×2、94% 即使 ROI 未達標仍續投、72% 親自主導、50% 認為工作前途繫於 AI 成敗、90% 預期 agent 今年見成效。</span></li>
<li><a class="ts" data-t="5127" href="https://www.youtube.com/watch?v=gfhpbXob6LY&t=5127" target="_blank" rel="noopener noreferrer">▶ 85:27</a> — <span class="outline-title">AI 四象限：從遲代到前瞻佈局</span><span class="outline-detail">AI 遲代 / 起步 / 規模化 / 前瞻佈局——2024 年前半兩類佔 26%，2025 年已拉到 40%。前瞻佈局企業的營收增長 1.7x、TSR 3.6x、利潤率 1.6x、專利 3.5x。</span></li>
<li><a class="ts" data-t="5727" href="https://www.youtube.com/watch?v=gfhpbXob6LY&t=5727" target="_blank" rel="noopener noreferrer">▶ 95:27</a> — <span class="outline-title">三種 AI 價值創造：Deploy / Reshape / Invent</span><span class="outline-detail">Deploy（用工具）KPI 升 10-15%；Reshape（端到端重塑職能）可到 30-90%；Invent（開創新商模）不是每家都要做。多數公司卡在 deploy。</span></li>
<li><a class="ts" data-t="6018" href="https://www.youtube.com/watch?v=gfhpbXob6LY&t=6018" target="_blank" rel="noopener noreferrer">▶ 100:18</a> — <span class="outline-title">10-20-70 法則與反直覺的資源配置</span><span class="outline-detail">AI 領先企業 70% 資源在人才組織流程、20% 在技術、10% 在演算法。多數公司問錯問題（&ldquo;該用哪個模型&rdquo;），因為真正瓶頸是組織而非工具。</span></li>
<li><a class="ts" data-t="6413" href="https://www.youtube.com/watch?v=gfhpbXob6LY&t=6413" target="_blank" rel="noopener noreferrer">▶ 106:53</a> — <span class="outline-title">歐洲生技公司 10 億歐元重塑案例</span><span class="outline-detail">CEO 定下省 10 億歐元的目標，聚焦商務/研發/行銷三個文件密集職能，光是燈塔專案就帶 2 億歐元價值。方法：Mirror Process A/B testing。</span></li>
<li><a class="ts" data-t="6774" href="https://www.youtube.com/watch?v=gfhpbXob6LY&t=6774" target="_blank" rel="noopener noreferrer">▶ 112:54</a> — <span class="outline-title">Q&amp;A：臺灣 CEO 的焦慮與盲點</span><span class="outline-detail">臺灣老闆都知道 AI 重要但 care 眼前生意；製造業 Winner 訂單能見度 30 個月、注意力被占滿，辦公室流程重塑被耽擱——這是臺灣 specific 的 5% 差異。</span></li>
<li><a class="ts" data-t="7156" href="https://www.youtube.com/watch?v=gfhpbXob6LY&t=7156" target="_blank" rel="noopener noreferrer">▶ 119:16</a> — <span class="outline-title">Top-Down 的水塔比喻</span><span class="outline-detail">JT：水塔在六樓、水要送到一樓，每層水管都要疏通；只通 6-5-4-3、2 樓堵住還是流不下來。這解釋為何 bottom-up 的點狀 AI 應用無法帶來端到端效益。</span></li>
<li><a class="ts" data-t="7357" href="https://www.youtube.com/watch?v=gfhpbXob6LY&t=7357" target="_blank" rel="noopener noreferrer">▶ 122:37</a> — <span class="outline-title">長期人才佈局：3-5 年消化 reshape 後的冗員</span><span class="outline-detail">拉長時間維度，reshape 後多出的人可 up-skill 做新事或不補新人自然消化，不一定要裁員。美國派的&ldquo;一半給 AI、一半給人&rdquo;不是唯一解。</span></li>
<li><a class="ts" data-t="7711" href="https://www.youtube.com/watch?v=gfhpbXob6LY&t=7711" target="_blank" rel="noopener noreferrer">▶ 128:31</a> — <span class="outline-title">代理的風險 vs 不作為的代價</span><span class="outline-detail">JT：&ldquo;Cost of inaction&rdquo; 比想象的風險更高——用 Mirror Process + pilot 實測才是判斷風險與準度的正確方法，不是關起門來靠想象。</span></li>
<li><a class="ts" data-t="8044" href="https://www.youtube.com/watch?v=gfhpbXob6LY&t=8044" target="_blank" rel="noopener noreferrer">▶ 134:04</a> — <span class="outline-title">小公司反而是 AI 贏家候選</span><span class="outline-detail">小公司優勢：CEO 容易被說服、投資不需大、靈活。&ldquo;一人加上一堆 AI 工具能做大公司百人的事&rdquo;——不一樣的挑戰和機會。</span></li>
<li><a class="ts" data-t="8133" href="https://www.youtube.com/watch?v=gfhpbXob6LY&t=8133" target="_blank" rel="noopener noreferrer">▶ 135:33</a> — <span class="outline-title">結尾：未來經理人論壇 + AI Taiwan 商務展</span><span class="outline-detail">數位時代七月未來經理人論壇（主題 AI for Impact）、6/24-26 圓山花博 AI Taiwan 未來商務展預告。</span></li>
"""

META_OBJ = {
    "videoId": VIDEO_ID,
    "title": TITLE,
    "channel": CHANNEL,
    "duration": DURATION,
    "publishDate": PUBLISHED,
    "generationDate": "2026-04-19",
    "summary": "數位時代 2026 直播論壇，三位講者（王志仁/簡立峰/徐瑞廷）從趨勢、人才、落地三視角剖析 AI 成效戰——核心：95% 企業 AI 投資沒成效是因為缺乏端到端職能重塑，Top-Down + 10-20-70 + Mirror Process 是領先企業的共通配方。",
    "tags": ["ai", "企業轉型", "臺灣", "商業管理", "論壇"],
    "keywords": [
        "10-20-70 法則",
        "Reshape vs Deploy",
        "Reshape 四原則",
        "B2B Agentic Commerce",
        "Work Faster → Work Smarter",
        "臺灣認知落差",
        "組織賦能 > 員工賦能",
        "FDE（Forward Deploy Engineer）",
    ],
    "filename": "2026-04-19-010100-video-lens_gfhpbXob6LY_ai_2026_forum_effectiveness.html",
}

OUT_PATH = Path.home() / "Downloads/video-lens/reports" / META_OBJ["filename"]

# Build the payload for render_report.py
payload = {
    "VIDEO_ID": VIDEO_ID,
    "VIDEO_TITLE": TITLE,
    "VIDEO_URL": VIDEO_URL,
    "META_LINE": META_LINE,
    "SUMMARY": SUMMARY,
    "TAKEAWAY": TAKEAWAY,
    "KEY_POINTS": KEY_POINTS.strip(),
    "OUTLINE": OUTLINE.strip(),
    "DESCRIPTION_SECTION": "",
    "VIDEO_LENS_META": json.dumps(META_OBJ, ensure_ascii=False),
}

# Find render_report.py
render_script = None
for base in [Path.home() / ".claude", Path.home() / ".agents"]:
    candidate = base / "skills/video-lens/scripts/render_report.py"
    if candidate.exists():
        render_script = str(candidate)
        break
if not render_script:
    print("ERROR: render_report.py not found", file=sys.stderr)
    sys.exit(1)

print(f"Rendering to: {OUT_PATH}", flush=True)
result = subprocess.run(
    ["python", render_script, str(OUT_PATH)],
    input=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
    capture_output=True,
)
print("STDOUT:", result.stdout.decode("utf-8", errors="replace"))
print("STDERR:", result.stderr.decode("utf-8", errors="replace"))
print("RC:", result.returncode)
if result.returncode == 0:
    size = OUT_PATH.stat().st_size
    print(f"OK path={OUT_PATH} size={size} bytes")
