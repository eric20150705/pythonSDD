# 資料模型：抽取方塊與槍械

## 座標與計時慣例

- 世界座標使用 `x/z` 表示水平平面，`y` 表示高度；玩家、子彈、抽取預覽與建築物使用三維浮點座標。
- 模擬維持固定 60 FPS；射擊、抽取動畫、子彈生命週期、特效與重生都以整數幀計算。
- 建築互動距離維持 `MAX_PICK_DISTANCE = 60.0` 世界單位。
- 抽取觸發距離為 `PULL_TRIGGER_PIXELS = 24` 畫面像素，成功抽取預覽為 `PULL_ANIMATION_FRAMES = 10` 幀。
- 子彈以 `BULLET_SPEED = 1.6` 世界單位／幀移動，最長 `BULLET_LIFETIME_FRAMES = 45` 幀或 `BULLET_MAX_DISTANCE = 60.0` 世界單位。
- 連射間隔為 `FIRE_INTERVAL_FRAMES = 6`，每個完整分段需要 `BULLET_HITS_TO_BREAK = 10` 次有效命中。
- 建築分段於 `RESPAWN_FRAMES = 1800` 幀後進入既有支撐感知的重生流程；固定 60 FPS 下約為 30 秒。
- 子彈集合最多 `MAX_BULLETS = 256`；效果與碎片沿用既有 `MAX_EFFECTS = 256`、`MAX_DEBRIS = 512` 上限。
- 背景採固定淺藍色 `SKY_COLOR = (170, 220, 245)`；遠景渲染距離為 180，細節距離為 110 世界單位。

## 實體

### SessionState（場次狀態）

代表一次從啟動到離開的沙盒場次，負責暫存輸入、投射物與部分傷害狀態。

| 欄位 | 型別／形狀 | 規則 |
|---|---|---|
| `world_seed` | 整數 | 場次開始時建立；控制活動區與遠景區塊的可重現布局。 |
| `player` | Player | 正好一個活動玩家；擁有槍械持有與裝備狀態。 |
| `camera` | Camera | 跟隨玩家並擁有環視角度。 |
| `active_chunks` | 對應 `(chunk_x, chunk_z) -> CityChunk` 的映射 | 正常運作時正好是目前 3×3 的互動集合；碰撞與目標查找只使用此集合。 |
| `visible_chunks` | 對應 `(chunk_x, chunk_z) -> CityChunk` 的映射 | 有界的 5×5 渲染集合，包含活動區塊；外圈區塊只供渲染。 |
| `respawn_overrides` | 對應 `segment_key -> RespawnRecord` 的映射 | 既有的已毀分段排程；活動區塊卸載後仍保留，直到支撐恢復。 |
| `damage_overrides` | 對應 `segment_key -> 整數` 的映射 | 本場次完整分段的部分子彈命中；數值為 0–9，分段倒塌或重生時移除。 |
| `counted_segment_keys` | 穩定分段識別集合 | 既有的一次性唯一拆除識別；此處不儲存幾何。 |
| `destroyed_count` | 非負整數 | 每個穩定分段識別只增加一次，且本場次不會減少。 |
| `bullets` | Bullet 清單 | 活動投射物；先移除失效子彈，若仍達 `MAX_BULLETS`，加入新彈前先移除最舊的活動子彈。 |
| `pull_action` | PullAction 或 null | 最多一個活動抓取／抽取操作；取消、完成或失焦時清除。 |
| `held_mouse_buttons` | 滑鼠按鍵識別集合 | 追蹤左鍵連射或抽取輸入；放開、失焦與離開時清除。 |
| `cursor_position` | `(x, y)` | 用於目標選取與子彈瞄準的最新游標位置。 |
| `screen_size` | `(width, height)` | 最新渲染尺寸，用於將游標位置轉為瞄準射線。 |
| `hud` | HUDState | 提供玩家看見的模式、目標、命中進度、拆除數與重生資訊。 |
| `running` | 布林值 | 收到 `Esc`、關窗或相等的離開事件後為 False。 |

### Player（玩家）

| 欄位 | 型別／形狀 | 規則 |
|---|---|---|
| `position` | `Vector3` | 既有移動與安全恢復位置。 |
| `velocity` | `Vector3` | 既有移動、重力與碎片推力速度。 |
| `grounded` | 布林值 | 既有地面／支撐碰撞狀態；不會造成拆除。 |
| `last_safe_position` | `Vector3` | 既有恢復位置。 |
| `has_gun` | 布林值 | 新場次永遠為 true；本功能不加入拾取或物品欄進程。 |
| `gun_equipped` | 布林值 | 初始為 false；由按鍵 `1` 切換。False 選擇抽取模式，true 選擇槍械模式。 |
| `fire_cooldown_frames` | 整數 | 倒數至零；控制下一發自動射擊，且不得小於零。 |
| `slow_until_frame` | 整數 | 既有碎片減速計時器。 |
| `pending_push` | `Vector3` | 既有暫存碎片衝量。 |
| `size` | `Vector3` | 既有玩家 AABB 尺寸。 |

玩家狀態轉換：

```text
START -> HAS_GUN + HOLSTERED
HOLSTERED --1--> EQUIPPED
EQUIPPED --1--> HOLSTERED
HOLSTERED + 左鍵拖曳 -> PullAction.DRAGGING 或 CANCELLED
EQUIPPED + 左鍵持續按住 -> FIRING（依固定間隔發射子彈）
ANY --Esc／視窗失焦--> INPUT_CLEARED
```

### PullAction（抽取操作）

代表一次明確的抓取與抽出手勢。由場次擁有，因為它依賴游標輸入與活動世界查找。

| 欄位 | 型別／形狀 | 規則 |
|---|---|---|
| `segment_id` | 穩定分段識別 | 建立時必須指向活動互動集合中的完整分段。 |
| `start_cursor` | `(x, y)` | 開始抓取時的游標位置。 |
| `current_cursor` | `(x, y)` | 左鍵按住期間的最新游標位置；與 `start_cursor` 的畫面位移驅動僅渲染預覽偏移。 |
| `drag_distance` | 非負浮點數 | 從起點算起的畫面距離；成功門檻為 24 像素。 |
| `phase` | `DRAGGING` 或 `ANIMATING` | `DRAGGING` 顯示進度；`ANIMATING` 完成抽取。 |
| `progress` | 浮點數 0–1 | 供渲染使用的標準化拖曳或動畫進度，並限制在 0–1。 |
| `offset_direction` | `Vector3` | 保留相機面向基準供預覽計算使用；實際渲染偏移由目標目前深度的 `current_cursor - start_cursor` 推導，不能寫回分段變換。 |
| `remaining_frames` | 整數或 null | 成功放開後的十幀動畫倒數。 |

抽取轉換：

```text
NONE --對有效目標按下左鍵--> DRAGGING
DRAGGING --移動不足 24 px 後放開左鍵--> NONE（取消）
DRAGGING --目標失效／模式變更／視窗失焦--> NONE（取消）
DRAGGING --移動達 24 px 後放開左鍵--> ANIMATING
ANIMATING --完成 10 幀--> 拆除目標，然後回到 NONE
```

只有 `ANIMATING` 完成時才呼叫既有拆除與支撐連鎖規則。完成前的預覽偏移只影響畫面，會在目標目前相機深度跟隨游標位移，且不會建立第二個碰撞物件。

### Bullet（子彈）

代表由已裝備槍械發射的可見投射物。

| 欄位 | 型別／形狀 | 規則 |
|---|---|---|
| `position` | `Vector3` | 從玩家武器槍口開始，每個固定幀前進。 |
| `velocity` | `Vector3` | 標準化瞄準方向乘以 `BULLET_SPEED`。 |
| `remaining_frames` | 整數 | 初始為 `BULLET_LIFETIME_FRAMES`；遞減至零後移除子彈。 |
| `distance_travelled` | 非負浮點數 | 達到 `BULLET_MAX_DISTANCE` 後移除子彈。 |
| `size` | `Vector3` | 小型視覺尺寸；不影響玩家碰撞。 |

子彈轉換：

```text
NONE --已拿槍 + 持續按住左鍵 + 冷卻為零--> ACTIVE
ACTIVE --掃掠命中最近的完整活動分段--> HIT，造成一次傷害後移除
ACTIVE --距離／生命週期達上限--> EXPIRED，移除
ACTIVE --分段不再有效--> 繼續或無傷害結束
```

子彈不與僅渲染遠景區塊、玩家、下落碎片或缺失分段互動。

### CityWorld 與可見區域

既有 `active_chunks` 仍是遊戲規則的權威集合。`visible_chunks` 是依相同世界種子與座標規則產生的有界呈現集合。

| 區域 | 內容 | 碰撞 | 目標／傷害 | 渲染 |
|---|---|---|---|---|
| 活動 3×3 | 目前互動區塊與其中的完整分段 | 有 | 有 | 在細節上限內繪製詳細分段，否則使用輪廓替代 |
| 遠景外圈 | 5×5 可見集合內最多 16 個額外區塊 | 無 | 無 | 每棟建築繪製一個可重現的建築輪廓 |

玩家更換區塊時，活動區塊保持既有卸載／重載行為。可見外圈會依新的 5×5 座標集合重新產生或裁剪，永遠不得無界增長。遠景區塊只有進入活動 3×3 集合後才變成可互動。

### BuildingSegment（建築分段）

既有建築分段，新增部分傷害欄位。

| 欄位 | 型別／形狀 | 規則 |
|---|---|---|
| `segment_id` | 穩定識別 `(building_id, floor, column, part)` | 用於目標、傷害、計數與重生的識別。 |
| `local_position` | `Vector3` | 相對於建築物的原始位置。 |
| `size` | `Vector3` | 原始長方體尺寸。 |
| `kind` | `COLUMN` 或 `SLAB` | 既有視覺與支撐類別。 |
| `status` | `INTACT`、`FALLING`、`ABSENT`、`PENDING_RESPAWN` | 只有 `INTACT` 參與碰撞、目標與子彈命中測試。 |
| `bullet_hits` | 完整分段為整數 0–9 | 對應場次 `damage_overrides`；達到 10 後立即透過既有拆除函式轉換，並重設此值。 |
| `destroyed_frame` | 整數或 null | 既有破壞時間戳。 |
| `respawn_frame` | 整數或 null | 既有的 `destroyed_frame + RESPAWN_FRAMES`；恢復後清除。 |
| `counted` | 布林值 | 既有一次性計數標記，由 `counted_segment_keys` 初始化。 |

部分傷害不是支撐狀態。在第十次有效命中造成正常拆除前，它不會改變分段的 AABB 或支撐邊。

### HUDState（HUD 狀態）

| 欄位 | 型別／形狀 | 規則 |
|---|---|---|
| `weapon_state` | `HOLSTERED` 或 `EQUIPPED` | 對應 `Player.gun_equipped`。 |
| `mode_hint` | 文字 | 說明「左鍵拖曳抽取」或「按住左鍵射擊」。 |
| `target_segment` | 分段識別或 null | 游標下最近的可見、完整、活動分段；可在一幀完成回饋中保留剛拆除的識別。 |
| `target_hits` | 整數 0–10 或 null | `target_segment` 的目前子彈進度；`10` 是清除已拆除目標前的一幀完成回饋，null 表示沒有目標或回饋。 |
| `completion_feedback_frames` | 整數 0–1 | 計算第十次命中後顯示 `target_hits=10` 的單一渲染幀；歸零後才清除目標回饋。 |
| `destroyed_count` | 整數 | 對應場次的唯一拆除數。 |
| `respawn_remaining` | 整數秒數或 null | 既有最近重生倒數，限制為不小於零。 |

### 拆除與重生狀態

既有支撐圖與生命週期仍是權威規則：

```text
INTACT --成功抽取--> FALLING
INTACT --第十次有效子彈命中--> FALLING
INTACT --失去支撐--> FALLING
FALLING --碎片生命週期結束--> ABSENT
ABSENT --重生幀到達 + 支撐可用--> INTACT
ABSENT --重生幀到達 + 沒有支撐--> PENDING_RESPAWN
PENDING_RESPAWN --支撐恢復--> INTACT
```

每次進入 `FALLING` 都使用既有拆除特效、唯一拆除數登記與重生記錄。只有玩家接觸不會造成任何轉換。

## 核心不變量

1. `active_chunks` 必須維持正好 3×3 的遊戲規則集合，可見集合永遠不得超過 25 個區塊。
2. 完整分段仍提供玩家/建築碰撞，但玩家接觸永遠不得呼叫拆除。
3. 抽取只有在拖曳達 24 像素且完成 10 幀動畫後才提交；未完成抽取不影響遊戲規則。
4. 單發子彈在移除前最多傷害一個最近的完整活動分段；分段必須正好 10 次有效命中才拆除，並提供一幀 `10/10` HUD 完成回饋。
5. `damage_overrides` 只包含完整分段的部分傷害；分段倒塌或重生時清除，玩家單獨重生不清除完整分段進度。
6. 穩定分段識別在重複射擊、抽取、重生與區塊重載後，`destroyed_count` 最多增加一次。
7. 子彈、特效、碎片與可見區塊都維持有界；先清除失效子彈，再於達上限時淘汰最舊活動子彈，所有計時器都會歸零並正常結束。
8. 僅渲染遠景建築永遠不參與碰撞、目標選取、子彈傷害或拆除計數。
9. `gun_equipped` 是唯一的左鍵模式切換；右鍵相機環視會抑制左鍵互動，失焦/離開會清除暫存抽取與射擊輸入。
10. 不新增生命值、死亡、彈藥、換彈、勝利、失敗或跨場次持久化狀態。
11. 抽取處於 `DRAGGING` 或 `ANIMATING` 時，目標預覽會依抓取點的水平、垂直與斜向游標位移跟隨；預覽偏移只供渲染，永遠不改變目標實際位置、AABB、支撐圖、傷害進度或拆除計數。
