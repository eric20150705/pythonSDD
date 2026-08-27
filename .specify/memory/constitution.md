<!--
Sync Impact Report
- Version change: 1.1.0 → 1.2.0
- Modified principles: None
- Added sections: Git Branch Naming and Pull Request Lifecycle under Governance
- Removed sections: None
- Follow-up TODOs: None
-->

<!--
Sync Impact Report
- Version change: 1.0.0 → 1.1.0
- Modified principles:
  - Playable Increment First → Playable Increment First（先完成可玩的最小切片）
  - Clear Python Fundamentals → Python/Pygame Fundamentals Before Advanced Architecture
  - Recognizable Game-Loop Responsibilities → Explicit Game-Loop Responsibilities
  - Verify Before Expanding → Verify Behavior Before Expanding
  - Safe, Incremental Refactoring → Safe, Incremental Refactoring
- Added sections: Capability Baseline within Learning Scope and Project Constraints;
  explicit state invariants in Development Workflow and Quality Gates
- Removed sections: None
- Follow-up TODOs: None
-->

# Python Pygame Learning Project Constitution

## Core Principles

### I. Playable Increment First（先完成可玩的最小切片）

每個功能 MUST 從最小、可執行且能被玩家觀察的切片開始。切片 MUST 先定義玩家
輸入、狀態變化、畫面回饋、成功條件，以及邊界或失敗行為。新機制 MUST 一次只
加入一個主要變化，並在執行中的遊戲確認後，才可與其他效果合併。

理由：專案已從函式與 Pygame 視窗逐步發展到磚塊、底板、球、碰撞、計分、生命、
特殊磚塊、粒子、煙火與勝負狀態。垂直切片能讓每次修改的因果關係保持清楚。

### II. Python/Pygame Fundamentals Before Advanced Architecture

程式碼 MUST 優先使用可讀的名稱、集中管理的可調整常數、小型函式，以及讓相關
狀態與行為放在一起的簡單類別。串列、字典、迴圈、property、pygame.Rect、
pygame.Vector2、計時器、random 與 math 等技術可直接使用，因為它們已在專案中
被實際運用。設計模式、型別系統、框架、額外套件或其他進階抽象 MUST 只有在目前
功能有明確需求時才導入，且計畫 MUST 說明它解決的問題與使用方式。

理由：目前程式碼顯示已具備基礎至初中階的 Python/Pygame 實作能力，但尚未建立
測試基礎設施、型別註記或多模組架構。憲章必須讓能力逐步成長，不能用超出目前
需求的架構取代對遊戲行為的理解。

### III. Explicit Game-Loop Responsibilities

主迴圈 MUST 保持輸入與事件、狀態更新、碰撞與規則、計時與特效、繪圖、畫面更新
等階段可被辨識。新增遊戲規則 MUST 指出狀態由誰擁有、在哪個更新階段改變，以及
玩家如何看見結果。Brick、Paddle、Ball、Explosion、Firework 等物件 MUST 將
自己的資料與直接行為放在同一個類別中；跨物件規則 SHOULD 放在目的單一的函式。
學習階段 MAY 保留單檔主程式，但新增大型系統前 MUST 在計畫中指出可抽出的責任
邊界。

理由：目前程式已能處理多球、碰撞、磚塊效果、粒子生命週期、煙火與勝負狀態。
明確的責任邊界可以在不要求一次重寫的前提下，控制單檔遊戲持續成長的複雜度。

### IV. Verify Behavior Before Expanding

功能完成前，受影響的 Python 檔案 MUST 通過語法或 AST 解析檢查，受影響的遊戲
路徑 MUST 完成手動 smoke test。測試 MUST 包含一條正常流程，以及至少一個相關
的邊界或失敗流程，例如離開遊戲、底板移動邊界、發射球、球遺失、磚塊碰撞、
遊戲勝利或遊戲結束。可從 Pygame 繪圖中分離的重複規則 SHOULD 使用標準庫
unittest 或其他已存在的測試工具建立自動化檢查。無法執行的檢查 MUST 記錄原因
與已知限制，不能默默略過。

理由：目前專案以視覺與互動行為為主，手動操作仍是必要驗證；碰撞、計分、計時器
與狀態轉換則適合逐步分離，讓自動化驗證能隨能力成長。

### V. Safe, Incremental Refactoring

重構 MUST 保留可執行的遊戲里程碑，且 MUST 與新玩法分開，除非沒有重構就無法
安全完成該功能。移動邏輯前 MUST 先用 smoke test 或自動化檢查記錄既有行為。
當檔案同時包含輸入、更新、碰撞、特效與繪圖時，後續工作 MUST 一次只抽出一個
責任；不得以大範圍重寫取代可追蹤的學習步驟。day1 與 day2 的歷史練習 MAY
保留原有形式，不得為了表面一致而全部改寫。

理由：day2/prj05.py 已形成大型單檔遊戲。小幅抽取能建立可維護習慣，也能保護
目前已經能執行的功能與學習成果。

## Learning Scope and Project Constraints

本憲章根據目前專案程式碼建立以下能力基線。開發者已能獨立處理函式、參數與
回傳值、條件與迴圈、串列與字典、常數、簡單類別與方法、Pygame 事件迴圈、
鍵盤控制、Rect 碰撞、Vector2 移動、計時器、隨機效果，以及基本遊戲狀態。
測試檔、型別註記、多模組架構與正式打包目前是逐步建立的學習目標，不是要求
立即全面重寫的前置條件。

- 專案 MUST 使用 Python 與 Pygame Community Edition 作為主要執行環境；執行時
  依賴 MUST 登記在 requirements.txt，新增依賴 MUST 說明必要原因。
- 目前遊戲以 60 FPS 的 frame-based timing 為基準。改用 delta time 或其他
  timing 模型前，計畫 MUST 說明原因，並驗證速度、計時器與碰撞行為沒有退化。
- 學習練習 MAY 以單檔與頂層主迴圈保存。新增的可變全域狀態 MUST 有清楚名稱，
  並在計畫或註解中說明其生命週期；當責任邊界已明確時，新增功能 MUST 優先
  考慮抽成函式或類別。
- 新增識別字 MUST 使用正確拼字且能表達用途；既有名稱只有在不擴大修改範圍時
  才修正。註解或 docstring MAY 使用中文，但 MUST 說明意圖或規則，而不是重複
  程式碼表面語法。
- 暫存編輯器輸出、bytecode cache、虛擬環境、憑證與機器專屬檔案 MUST NOT
  視為專案原始碼或納入功能提交。

## Development Workflow and Quality Gates

1. 在寫程式前，先記錄玩家行為、控制方式、狀態、畫面回饋、成功條件與失敗或
   邊界條件。
2. 從現有類別、函式與常數中選出一個可完成的垂直切片，並列出預計修改的責任。
3. 以最小修改完成切片，保持輸入、更新、碰撞、特效與繪圖的責任順序可辨識。
4. 對受影響的 Python 目錄執行語法檢查，並啟動相關腳本完成手動 smoke test。
   測試結果 MUST 記錄在功能筆記、計畫或提交說明中。
5. 含有重複規則的功能 MUST 驗證下列適用的不變量：
   - 活躍球數不得超過 MAX_BALLS。
   - 生命值只可因明確的失球或生命效果改變，且遊戲結束後不得繼續扣減。
   - 磚塊分數 MUST 只在磚塊真正被摧毀時增加一次。
   - 計時器 MUST 遞減至零，不得因更新流程產生不受控的負值或永久效果。
   - game_over 與 game_won MUST 不可同時為真。
6. 當碰撞、計分、計時器或狀態轉換已能與繪圖分離時，MUST 增加一個聚焦的
   自動化檢查；檢查可使用 Python 標準庫，不得為了測試而不必要地擴增依賴。
7. 在開始下一個切片前，依本憲章檢查複雜度、驗證結果與已知限制。任何例外
   MUST 記錄被跳過的規則、原因、保護的行為與後續處理方式。

## Governance

本憲章定義專案的開發優先順序，優先於方便但未經說明的程式習慣。功能規格、
計畫、任務清單與程式碼檢查 MUST 對照本憲章。若需求與憲章衝突，實作前 MUST
在相關設計文件中明確記錄衝突、選擇與影響。

### Git Branch Naming and Pull Request Lifecycle

- 使用 Spec-kit 建立的功能分支 MUST 採用 `###-feature-name` 格式：`###` 是三位數
  功能編號，`feature-name` MUST 是小寫、以連字號分隔的簡短描述，不得包含空白、
  中文或未說明的特殊字元。例如本功能分支應為 `001-dynamic-demolition-sandbox`。
- Git 分支名稱 MUST 與對應的 `specs/###-feature-name/` 目錄及規格文件中的
  `Feature Branch` 欄位完全一致，不得額外加入前綴或後綴。
- 功能分支 MUST 從預設整合分支建立，功能變更 MUST 透過 Pull Request 合併，
  不得直接將功能提交推送至預設整合分支。
- Pull Request MUST 連結或指向對應的 spec、plan 與 tasks 文件，並記錄適用的
  語法檢查、自動化測試與手動 smoke test 結果；未完成的品質門檻 MUST 明確列出。
- Pull Request 確認合併成功後，來源分支 MUST 從遠端刪除，並同步從本地刪除；
  分支清除 MUST 在交付紀錄中確認，避免已合併分支持續被使用。

專案擁有者可依學習目標、技術選擇或維護需求修訂本憲章。每次修訂 MUST 更新
檔案最上方的 Sync Impact Report、說明變更原因、更新語意版本與 Last Amended
日期。移除或重新定義核心原則是 MAJOR；新增原則、章節或大幅擴充規範是 MINOR；
澄清文字、修正拼字或不改變治理意義的調整是 PATCH。

每個功能檢查 MUST 確認已有可觀察的遊戲結果、完成適用的語法與 smoke test、
驗證相關狀態不變量，並記錄任何限制。若某條規則被反覆違反，或已不再支持
學習目標，必須修訂憲章或在設計文件中提出例外；程式碼不得無聲繞過規則。

**Version**: 1.2.0 | **Ratified**: 2026-08-26 | **Last Amended**: 2026-08-27
