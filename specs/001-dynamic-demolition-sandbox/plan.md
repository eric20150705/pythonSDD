# Implementation Plan: Dynamic Demolition Sandbox

**Branch**: `001-dynamic-demolition-sandbox` | **Date**: 2026-08-26 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/001-dynamic-demolition-sandbox/spec.md`

## Summary

建立 NEON CITY 的第一個完整可玩原型：玩家以第三人稱方塊人探索沒有固定邊界的程序化城市，使用 WASD、Space、右鍵鏡頭與左鍵拆樓。城市以固定大小區塊串流，附近維持 30–54 棟大樓；每棟大樓由樓層與柱狀分段組成，破壞支撐後以可控的簡化重力連鎖坍塌，碎片會推開／減速玩家，分段約 30 秒後重生。

實作採既有 Python／pygame-ce 學習專案的最小增量：新增獨立的 `game_3d.py`，以 `pygame.Vector3`、自製透視投影與 AABB／支撐圖規則完成軟體 3D；不改寫 `day1`／`day2`，不引入外部 3D 或物理引擎。

## Technical Context

**Language/Version**: Python 3.14.0（已在專案虛擬環境驗證）

**Primary Dependencies**: `pygame-ce==2.5.8`；使用標準庫 `math`、`random`、`unittest`。`pygame.Vector3` 已在目前環境驗證可用。

**Storage**: 僅保存在記憶體中的單次遊戲狀態；不建立存檔、不使用資料庫。

**Testing**: `unittest` 驗證純規則與狀態轉換；`py_compile`／AST 語法檢查；無視窗自我檢查；Windows 上的手動遊戲 smoke test。

**Target Platform**: Windows 桌面電腦，鍵盤與滑鼠，1280×720 可調整視窗。

**Project Type**: 單一入口的桌面遊戲原型。

**Performance Goals**: 目標 60 FPS；玩家附近固定 3×3 區塊中維持 30–54 棟大樓（出生安全區排除後仍至少 30 棟）；正常探索 15 分鐘內保持可操作。

**Constraints**: 只使用現有 `pygame-ce` 依賴；不使用外部模型、圖片、音效、網路、存檔、多人或完整剛體物理；固定 60 FPS frame-based simulation 以符合專案憲章；遠處區塊必須回收，避免幾何、碎片與效果狀態無限制累積；本局只額外保留必要的 key-only 拆除統計索引。

**Scale/Scope**: 一個單人沙盒場次；每區塊約 4–6 棟大樓，每棟約 4–12 層，作用中世界維持固定 3×3 區塊，區塊交換時最多暫存 1 個待載入區塊；第一版只做普通方塊人與核心拆樓循環。

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Plan evidence |
|---|---|---|
| I. Playable Increment First | PASS | 依序完成可啟動視窗、角色／鏡頭、單區塊大樓、拆除／坍塌、串流／重生與 HUD；每個切片都有輸入、狀態、回饋與 smoke test。 |
| II. Python/Pygame Fundamentals Before Advanced Architecture | PASS | 保持 Python、pygame-ce、簡單類別與小型函式；軟體 3D 是 3D 需求所必要的最小抽象，不新增引擎或複雜框架。 |
| III. Explicit Game-Loop Responsibilities | PASS | 主迴圈固定分為事件／輸入、世界更新、碰撞與破壞、計時／特效、投影繪圖、畫面更新；Player、Camera、Building、Segment、Debris 各自擁有直接資料與行為。 |
| IV. Verify Behavior Before Expanding | PASS | 每個垂直切片先做 `unittest`／語法檢查與手動 smoke test；覆蓋正常流程、空點擊、無限連跳、區塊回收、連鎖坍塌與重生。 |
| V. Safe, Incremental Refactoring | PASS | 新遊戲使用根目錄獨立入口，不碰 `day1`／`day2`；只有在規則可分離時才抽出純函式與測試介面。 |

固定 frame-based simulation 是刻意保留既有專案的 60 FPS 模型，不切換成 delta time；因此移動、重力、碰撞、重生與特效計時都以固定更新步驟驗證，避免在學習專案中同時引入新的 timing 變因。

## Project Structure

### Documentation (this feature)

```text
specs/001-dynamic-demolition-sandbox/
├── plan.md                 # 本文件
├── research.md             # Phase 0 的技術決策與取捨
├── data-model.md           # Phase 1 的狀態、關係與不變量
├── quickstart.md           # 執行與端到端驗證指南
├── contracts/
│   └── ui-controls.md      # 鍵盤、滑鼠與畫面回饋契約
└── tasks.md                # 由 $speckit-tasks 產生，本階段不建立
```

### Source Code (repository root)

```text
game_3d.py                 # 新增：遊戲入口、世界、角色、鏡頭、投影與主迴圈
tests/
└── test_game_3d.py        # 新增：純規則、投影、生成、破壞與重生測試
README.md                  # 更新：啟動、控制、self-test 與限制
requirements.txt           # 保持 pygame-ce==2.5.8，不新增依賴
day1/                      # 保留既有練習，不修改
day2/                      # 保留既有練習，不修改
```

**Structure Decision**: 選擇單一新入口加清楚責任區塊，符合目前學習專案與憲章對單檔主迴圈的容許範圍；測試只依賴可與繪圖分離的純規則。大型責任邊界會在 `game_3d.py` 內以類別、資料結構與單一目的函式明確分隔，等核心玩法穩定後再考慮後續多模組切片。

## Implementation Sequence

1. **可執行骨架與投影**：建立視窗、固定 60 FPS 主迴圈、`Vector3` 座標、近裁切與透視投影、方塊繪製、退出事件與 `--self-test` 入口。
2. **角色與鏡頭垂直切片**：加入方塊人、地面、WASD camera-relative movement、單段跳躍、右鍵環繞鏡頭、地面／靜態方塊碰撞與掉落恢復。
3. **固定區塊城市與動態串流**：以世界種子與區塊座標產生 4–6 棟大樓，加入樓層、柱狀分段、深度排序、霓虹面色、起點安全區與玩家周圍 3×3 區塊串流。
4. **破壞與支撐圖**：加入滑鼠最近可見分段選取、碰撞破壞冷卻、分段狀態轉換、以地面為根的支撐可達性判定與連鎖坍塌。
5. **碎片、推動與重生**：加入下落碎片、有限生命週期、玩家推開／減速、一次性拆除計數、逐段 30 秒重生與由下而上的支撐恢復。
6. **HUD 與整合回饋**：加入目標提示、拆除數、倒數、操作說明、閃光／粒子／鏡頭震動與串流狀態整合。
7. **驗證與文件**：完成標準庫測試、語法／AST 檢查、headless self-test、手動 smoke test，更新 README 並記錄已知限制。

## Phase 1 Design Decisions

- **座標系**：`x/z` 為水平平面，`y` 為高度；世界單位使用浮點數，區塊大小 32×32。
- **區塊生成**：用啟動時世界種子加 `(chunk_x, chunk_z)` 的穩定混合值建立區塊專屬 `random.Random`；同一局回到區塊時布局一致，重新啟動時整個世界重置。
- **active set**：玩家所在區塊為中心，正常狀態精確維持 3×3（9 個）區塊；交換的一個更新步驟最多額外保留 1 個待載入區塊，載入完成後同一更新步驟移除遠區塊，因此總載入上限為 10。每區塊生成 4–6 棟大樓，出生安全半徑排除後若作用中總數低於 30，生成器會改用確定性的合法備用地塊補足。
- **密度／安全區**：`CHUNK_SIZE=32`、`BUILDINGS_PER_CHUNK=4..6`、`MIN_ACTIVE_BUILDINGS=30`、`MAX_ACTIVE_BUILDINGS=54`、`SPAWN_SAFE_RADIUS=8.0`；備用地塊仍須通過 AABB 不重疊與出生安全半徑檢查。
- **透視／選取**：將可見立方體面投影成螢幕多邊形，依滑鼠位置命中測試與 camera-space depth 選擇最近完整分段；只有距玩家不超過 `MAX_PICK_DISTANCE=60.0` 世界單位的目標可被選取，空點擊、遮擋目標與超距離點擊不改變世界。
- **支撐／坍塌**：每棟樓的每一層有四個柱段。`floor=0` 的 `COLUMN(f,c)` 直接連到 `BASE`；`floor>0` 的 `COLUMN(f,c)` 只連到同一柱位的 `COLUMN(f-1,c)`；`SLAB(f)` 連到同層四個柱段。只有這些邊上的 `INTACT` 段可形成通往 `BASE` 的路徑；樓板在 v1 不作為柱鏈的垂直支撐。破壞後從地面做可達性搜尋，所有不可達完整分段在同一更新步驟進入 FALLING，避免用不穩定的隨機物理。
- **碰撞**：玩家與完整分段使用水平 AABB 加 `y` 範圍做阻擋；同一接觸以 `CONTACT_COOLDOWN_FRAMES=15` 防抖，FALLING／DEBRIS 不再提供靜態牆體碰撞。
- **時間**：所有移動、重力、粒子、碰撞冷卻與 30 秒重生以 60 FPS frame count 表示；例如重生使用 1,800 個 simulation frames。
- **串流破壞狀態**：遠處區塊回收時保存尚未恢復的 `(chunk, building, segment) -> respawn_frame` 覆寫；倒數到 0 但沒有支撐的分段保持 `PENDING_RESPAWN`，覆寫留到支撐恢復後才刪除，重新載入時重新套用狀態。已計數的 stable segment key 只保留為無幾何資料的本局統計索引，讓重生或重新載入不會重複增加唯一拆除數。
- **生命週期上限**：`DEBRIS_LIFETIME_FRAMES=180`、`DEBRIS_SLOW_FRAMES=30`、`MAX_EFFECT_LIFETIME_FRAMES=45`、`MAX_DEBRIS=512`、`MAX_EFFECTS=256`；特效依 `Effect` 的 `remaining_frames` 到期清除，超出上限時丟棄最舊的短命特效，不阻塞主迴圈。
- **拆除計數**：同一 stable segment key 在本局第一次進入 FALLING／ABSENT 時增加一次；重生後仍可再次點擊或碰撞，但不再增加本局唯一拆除數。快速點擊、碰撞與支撐重算共用同一 `counted`／統計索引。
- **視覺回饋**：完整、目標、FALLING、DEBRIS 使用不同霓虹色／透明度；拆除建立短命 flash／粒子／camera shake，不引入音效資產。

## Constitution Re-check (Post-Design)

| Gate | Result | Evidence |
|---|---|---|
| Playable increment | PASS | Implementation Sequence starts with a launchable projection slice and adds one major behavior per slice. |
| Python/Pygame scope | PASS | The design uses the verified runtime and standard-library data structures; no new framework or dependency is required. |
| Game-loop responsibilities | PASS | Input, update, collision/rules, timers/effects, projection/render and display are explicitly separated in the plan and data model. |
| Verification before expansion | PASS | `data-model.md`, `ui-controls.md` and `quickstart.md` define deterministic invariants and normal/boundary smoke paths before implementation expansion. |
| Safe refactoring | PASS | Only `game_3d.py`, its focused tests and README are in scope; `day1` and `day2` remain untouched. |

The design introduces no constitutional violation. Active geometry, debris and effects are bounded; timers expire, the key-only demolition count is idempotent, and the existing frame-based timing model is retained.
