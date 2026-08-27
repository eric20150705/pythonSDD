# Research: Dynamic Demolition Sandbox

**Feature**: `001-dynamic-demolition-sandbox`
**Date**: 2026-08-26

本階段研究以現有工作區、專案憲章、固定依賴與已確認的產品決策為主。所有高影響選擇均已收斂，研究階段已完成。

## Decision 1: Keep the existing Python/pygame runtime

**Decision**: 使用目前虛擬環境的 Python 3.14.0 與 `pygame-ce==2.5.8`，不新增第三方依賴。

**Rationale**: `requirements.txt` 已固定 pygame-ce；本地驗證顯示 `pygame.Vector3` 與 `pygame.Vector2` 可用，足以保存 3D 座標與完成投影。專案憲章要求 Python／Pygame 為主要執行環境，新增物理或 3D 引擎會擴大學習範圍與安裝風險。

**Alternatives considered**:

- Ursina／Panda3D：可減少鏡頭與投影工作，但會引入新依賴、資源格式與引擎生命週期，不符合本輪原型的學習邊界。
- 完整剛體物理套件：能提供更自然的碎片碰撞，但本需求只要求可理解的分段坍塌與玩家推動，不值得增加引擎複雜度。

## Decision 2: Software 3D with explicit projection

**Decision**: 使用 `Vector3` 世界座標、camera-space transform、近裁切與透視投影，把立方體面繪製到 pygame surface；以深度排序保證近面覆蓋遠面。

**Rationale**: 需求要 3D 城市，但現有依賴沒有通用 3D scene graph。自製最小投影可讓角色、城市、大樓分段、碎片與滑鼠選取使用同一套可測試資料；不需要外部模型或圖片。

**Alternatives considered**:

- 2D 假透視：可更快，但無法可靠支持第三人稱鏡頭、跳躍深度與分段選取。
- OpenGL／ModernGL：畫面能力更強，但會增加 context、shader、資源管理與平台差異，超出第一輪。

## Decision 3: Preserve fixed 60 FPS simulation

**Decision**: 以 `clock.tick(60)` 驅動固定 frame-based 更新；移動、重力、冷卻、特效與重生均以 frames 表示。

**Rationale**: 專案憲章明確以 60 FPS frame-based timing 為現行基準。新遊戲需要大量可重複的狀態測試，固定步驟能讓 `RESPAWN_FRAMES=1800`、支撐轉換與拆除計數容易驗證。

**Alternatives considered**:

- delta time：在不同 FPS 下速度更一致，但會改變既有 timing 模型，且需要額外驗證碰撞、重生與粒子行為；本輪先不引入。
- 完整 fixed timestep accumulator：品質較高，但對第一版單機原型增加主迴圈抽象；若 60 FPS smoke test 顯示不足，列為後續改進。

## Decision 4: Deterministic chunk streaming

**Decision**: 以 32×32 區塊、玩家周圍精確 3×3 active set、每區塊 4–6 棟大樓生成城市；由啟動種子與區塊座標決定布局，交換時最多暫存 1 個待載入區塊，遠處區塊在同一更新步驟回收。出生安全區排除後，作用中世界仍必須維持至少 30 棟、最多 54 棟大樓，必要時使用確定性的合法備用地塊。

**Rationale**: 能同時滿足「玩家移動時動態生成」與 30–54 棟城市密度，並限制投影、碰撞與碎片數量。穩定布局讓玩家回到已探索區域時不會看到城市突然重排；遠處只保留尚未恢復的破壞覆寫（包含已到 0 但等待支撐的狀態）與必要的 key-only 拆除統計，不保留幾何，避免無限探索造成幾何記憶體成長。

**Alternatives considered**:

- 永久保留所有區塊：探索狀態最完整，但與長時間沙盒的記憶體限制衝突。
- 每次載入都重新隨機：實作簡單，但會破壞回訪一致性與重生狀態。
- 更大的 5×5 active set：城市更密，但會提高每幀投影與碰撞成本；先以 3×3 建立可玩切片。

## Decision 5: Support graph instead of full physics

**Decision**: 大樓分段維護通往地面錨點的支撐邊；每層四個柱段形成四條垂直柱鏈，`floor=0` 柱段連到 `BASE`，上層柱段只連到同柱位的下一層下方柱段，每個樓板連到同層四柱，樓板不作為柱鏈的垂直支撐。破壞後以只穿越 `INTACT` 段的可達性搜尋決定哪些完整分段變為 FALLING。FALLING 物件只受簡化重力與有限生命週期影響，不做碎片彼此剛體堆疊。

**Rationale**: 支撐圖能產生可預測的「破壞支柱 → 上方連鎖坍塌」，且可測試「仍有支撐的區塊不落」。簡化下落足以提供重量感，並保護 60 FPS 與目前的 Python/Pygame 能力邊界。

**Alternatives considered**:

- 每個點擊只移除一個區塊：規則簡單，但無法達成連鎖坍塌的核心體驗。
- 完整剛體碰撞：效果更自然，但需要額外物理系統、碰撞穩定性與大量效能測試。

## Decision 6: Single entry point with pure-rule test seams

**Decision**: 新增 `game_3d.py`，在單檔內以 Player、Camera、CityWorld、CityChunk、Building、BuildingSegment、Debris、Effect 等清楚責任區塊組織；將生成、投影、命中、支撐、重生、效果與碰撞規則寫成可被 `unittest` 呼叫的函式／方法。

**Rationale**: 符合憲章允許的單檔學習階段，同時避免把所有規則埋在事件迴圈或繪圖函式裡。`day1`／`day2` 既有練習維持不變，新增測試只針對新遊戲。

**Alternatives considered**:

- 立即拆成多個正式模組：長期可維護性較好，但第一輪會增加跨模組介面與匯入複雜度，且尚未有穩定責任邊界。
- 直接改造 `day2/prj05.py`：會把打磚塊與 3D 沙盒混在同一檔案，違反安全增量重構原則。

## Resolved Unknowns

- 渲染方式：已決定使用 Pygame 軟體透視，不需要外部 3D 引擎。
- 物理方式：已決定使用支撐圖加簡化重力，不需要外部物理引擎。
- 儲存方式：已決定只保存單次遊戲記憶體狀態，分段約 30 秒重生，不做跨次存檔。
- 使用者介面：已決定第三人稱、右鍵旋轉、左鍵選取／破壞、WASD、Space、Esc。
- 測試方式：已決定標準庫 unittest、語法／AST、headless self-test 與手動 smoke test。
- 拆除計數：已決定以 stable segment key 做本局唯一計數；分段重生或重新載入後可以再次破壞，但不重複增加唯一拆除數。統計索引只保存 key，不保存遠處區塊幾何。
- 互動與生命週期邊界：已決定最大選取距離為 60 世界單位、碰撞冷卻為 15 frames、碎片生命週期為 180 frames、碎片減速為 30 frames、特效最長 45 frames、重生為 1,800 frames，且最多保留 512 個碎片與 256 個特效；玩家低於 -20.0 世界單位時回到最近安全位置。
- 可用性驗證：已決定在整合驗收時邀請 5 名未閱讀實作細節的測試者，只依 HUD 完成移動、跳躍、鏡頭與一次拆樓；至少 4 人完成才算通過。
