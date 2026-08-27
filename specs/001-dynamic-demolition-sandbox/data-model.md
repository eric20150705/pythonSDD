# Data Model: Dynamic Demolition Sandbox

## Coordinate and Timing Conventions

- 世界座標使用 `x/z` 表示水平平面，`y` 表示高度；玩家與物件位置使用三維浮點座標。
- 一個城市區塊大小為 32×32 世界單位；玩家所在區塊周圍精確 3×3（9 個）區塊為 active set。
- 模擬以 60 FPS 固定 frame 更新；所有計時器使用整數 frame。
- `RESPAWN_FRAMES = 1800` 代表約 30 秒；所有倒數不得小於零。

### Fixed Runtime Bounds

- `CHUNK_SIZE = 32` 世界單位。
- `BUILDINGS_PER_CHUNK = 4..6`；出生安全區排除後，`MIN_ACTIVE_BUILDINGS = 30`，`MAX_ACTIVE_BUILDINGS = 54`。
- `SPAWN_SAFE_RADIUS = 8.0` 世界單位；生成器必須使用合法備用地塊補足作用中世界密度，不得以安全區為理由降低 30 棟下限。
- `MAX_PICK_DISTANCE = 60.0` 世界單位；`CONTACT_COOLDOWN_FRAMES = 15`。
- `DEBRIS_LIFETIME_FRAMES = 180`、`DEBRIS_SLOW_FRAMES = 30`、`MAX_EFFECT_LIFETIME_FRAMES = 45`、`MAX_DEBRIS = 512`、`MAX_EFFECTS = 256`。
- `RECOVERY_HEIGHT = -20.0` 世界單位；低於此高度時玩家回到最近的 `last_safe_position`。
- 正常載入 9 個區塊；交換期間最多 1 個 pending incoming chunk，包含 pending 時總載入數不得超過 10，且必須在同一更新步驟清理舊區塊。

## Entities

### SessionState

Represents one launch-to-exit sandbox session.

| Field | Type / Shape | Rules |
|---|---|---|
| `world_seed` | integer | Created once at session start; controls deterministic chunk layouts. |
| `player` | Player | Exactly one active player. |
| `camera` | Camera | Follows the player and owns orbit angles. |
| `active_chunks` | map `(chunk_x, chunk_z) -> CityChunk` | Normally contains exactly the 3×3 active set; during one swap it may include at most one pending incoming chunk, with total loaded chunks ≤ 10 before the old chunk is removed. |
| `respawn_overrides` | map `segment_key -> RespawnRecord` | Contains destroyed segments until they are restored; a record reaches ready-at-zero at its respawn frame and remains while the segment is `PENDING_RESPAWN`, then is removed only after supported restoration. |
| `counted_segment_keys` | set of stable segment keys | Records which segment identities have already contributed to the session's unique demolition count; it stores keys only, not geometry. |
| `destroyed_count` | non-negative integer | Increases once when a stable segment key first transitions into FALLING or ABSENT; never decreases during the session, including after respawn or chunk reload. |
| `debris` | list of Debris | Contains at most `MAX_DEBRIS`; expired debris is removed. |
| `effects` | list of Effect | Every effect has a finite lifetime and is removed at expiry. |
| `running` | boolean | False after quit event or window close. |

### Player

| Field | Type / Shape | Rules |
|---|---|---|
| `position` | `Vector3` | Kept above ground unless the recovery rule is triggered. |
| `velocity` | `Vector3` | Updated by input, gravity, collision response and debris push. |
| `grounded` | boolean | True only when the feet have a valid ground/support contact. |
| `last_safe_position` | `Vector3` | Updated after a stable ground contact in the active world. |
| `contact_cooldowns` | map `segment_key -> frame` | Prevents repeated demolition from one continuous contact. |
| `slow_until_frame` | integer | Debris slowdown ends at this frame, at most `DEBRIS_SLOW_FRAMES` after contact; never extends from a stale collision. |
| `pending_push` | `Vector3` | Transient horizontal debris impulse consumed by the next fixed player update, then cleared so input velocity cannot overwrite it. |

Player state transitions:

```text
GROUNDED --Space--> AIRBORNE --landing--> GROUNDED
GROUNDED/AIRBORNE --fall below recovery height--> RECOVERING -> GROUNDED
ANY --debris contact--> ANY + push/slow effect
```

### Camera

| Field | Type / Shape | Rules |
|---|---|---|
| `yaw` | angle | Updated only while right mouse drag is active. |
| `pitch` | angle | Clamped to prevent looking through the ground or flipping over. |
| `distance` | positive float | Fixed third-person distance in v1. |
| `target_offset` | `Vector3` | Looks near the player upper body. |
| `orbiting` | boolean | Mirrors right-button drag state. |

### CityChunk

| Field | Type / Shape | Rules |
|---|---|---|
| `coord` | `(chunk_x, chunk_z)` | Unique key in `active_chunks`. |
| `seed` | integer | Derived from `world_seed` and `coord`; same input yields same layout. |
| `buildings` | list of Building | 4–6 generated buildings after safety filtering; the active world generator uses deterministic legal fallback lots to keep the aggregate active count between 30 and 54. |
| `loaded_frame` | integer | Used for diagnostics and safe unload ordering. |

When a chunk is unloaded, its immutable layout is discarded and can be regenerated from `seed`; active `respawn_overrides` survive until expiry, while the session's key-only `counted_segment_keys` survives to preserve unique demolition counting. No unloaded chunk geometry is retained.

### Building

| Field | Type / Shape | Rules |
|---|---|---|
| `building_id` | stable string or tuple | Unique within the world coordinate space. |
| `origin` | `Vector3` | Base position; remains fixed for the session. |
| `width`, `depth` | positive float | Defines the footprint and collision bounds. |
| `floor_count` | integer, 4–12 | Determines generated vertical segments. |
| `segments` | map `segment_id -> BuildingSegment` | All original segments are regenerated from the same layout. |
| `support_edges` | map `segment_id -> set[segment_id or BASE]` | Defines paths that can keep a segment supported. |

### BuildingSegment

| Field | Type / Shape | Rules |
|---|---|---|
| `segment_id` | stable key `(building_id, floor, column, part)` | Unique and used by selection, counts and respawn overrides. |
| `local_position` | `Vector3` | Original location relative to the building. |
| `size` | `Vector3` | Original cuboid dimensions. |
| `kind` | `COLUMN` or `SLAB` | Determines visual treatment and support edges. |
| `status` | `INTACT`, `FALLING`, `ABSENT`, `PENDING_RESPAWN` | Only INTACT segments participate in static support and player blocking. |
| `destroyed_frame` | integer or null | Set on first destruction transition. |
| `respawn_frame` | integer or null | `destroyed_frame + RESPAWN_FRAMES`; cleared after restoration. |
| `counted` | boolean | Becomes true exactly once when the segment is counted; regenerated instances initialize this flag from `SessionState.counted_segment_keys`. |

Support topology is canonical in v1: each floor has four column positions `c=0..3` and one slab. For `floor=0`, `COLUMN(0,c)` has one support edge to `BASE`. For `floor>0`, `COLUMN(f,c)` has one support edge to `COLUMN(f-1,c)` at the same column position. `SLAB(f)` has support edges to all four `COLUMN(f,c)` segments on its own floor. Slabs are floor visuals in v1 and do not provide vertical support to the column chains. A segment is supported if it is reachable from `BASE` through support edges whose segment endpoints are `INTACT`. After a direct destruction, recalculate reachability for the building; every newly unreachable intact segment becomes `FALLING` in the same update step and receives its own respawn record.

Canonical support checks must demonstrate that destroying one upper column drops only that column's upper chain, destroying one ground-floor column drops its same-column chain while other supported columns and slabs remain, and destroying all ground-floor columns eventually removes support from every upper segment.

Segment transitions:

```text
INTACT --click/contact--> FALLING or ABSENT
INTACT --support lost--> FALLING
FALLING --debris lifetime ends--> ABSENT
ABSENT --respawn frame reached + supported--> INTACT
ABSENT --respawn frame reached + unsupported--> PENDING_RESPAWN
PENDING_RESPAWN --support restored--> INTACT
```

### Debris

| Field | Type / Shape | Rules |
|---|---|---|
| `source_segment_id` | segment key | Identifies the original segment and effect source. |
| `position` | `Vector3` | Starts at the segment's world position. |
| `velocity` | `Vector3` | Receives deterministic downward gravity and small demolition impulse. |
| `remaining_frames` | integer | Decrements to zero; then debris is removed. |
| `push_radius` | positive float | Contact zone for player push/slow effect. |

Debris is visual／dynamic only: it cannot provide building support, cannot block the player as a permanent wall, and cannot cause damage or game over.

### Effect

| Field | Type / Shape | Rules |
|---|---|---|
| `effect_id` | stable runtime identifier | Unique only while the effect is active. |
| `kind` | `FLASH`, `PARTICLE` or `CAMERA_SHAKE` | Determines the rendering or camera response. |
| `position` | `Vector3` | World position of the demolition feedback. |
| `remaining_frames` | integer | Starts at a lifetime no greater than `MAX_EFFECT_LIFETIME_FRAMES`, decrements every update and is removed at zero. |
| `intensity` | non-negative float | Bounded visual or camera response strength. |
| `source_segment_id` | segment key or null | Optional origin for diagnostics and HUD feedback. |

The active effect list is capped at `MAX_EFFECTS`; adding an effect over the cap removes the oldest short-lived effect first. Effects never participate in collision, support reachability or demolition counting.

### RespawnRecord

| Field | Type / Shape | Rules |
|---|---|---|
| `segment_key` | segment key | Identifies one original segment. |
| `respawn_frame` | integer | Must be greater than or equal to destruction frame; once reached, the record is ready at zero and does not become negative while support is pending. |
| `source_chunk` | chunk coordinate | Allows records to be re-applied when the chunk reloads. |

### HUDState

| Field | Type / Shape | Rules |
|---|---|---|
| `target_segment` | segment key or null | Current nearest visible segment under the cursor. |
| `destroyed_count` | integer | Mirrors SessionState count. |
| `respawn_remaining` | integer seconds or null | Shows the nearest relevant pending respawn, clamped at zero. |
| `control_hint` | text | Shows the fixed keyboard/mouse controls. |

## Core Invariants

1. `active_chunks` contains exactly 9 current chunks in normal operation and at most one pending incoming chunk during a swap; total loaded chunks never exceeds 10.
2. A stable segment key can increase `destroyed_count` only once, even if clicked, collided with, later found unsupported, respawned or reloaded.
3. `INTACT` is the only static building state; FALLING, ABSENT and PENDING_RESPAWN never block as original geometry.
4. Respawn countdowns and all effect timers reach zero; effects are removed at expiry, while a ready respawn record may remain at zero until its segment is supported and restored, and no timer becomes permanently negative or any effect remains active forever.
5. A segment that respawns without a support path cannot become `INTACT` until its support path exists.
6. `grounded` is false during an airborne jump, so Space cannot trigger an additional jump.
7. No game-over or game-won state is needed for this sandbox; both are absent from the session state.
8. The active world contains at least 30 and at most 54 generated buildings after spawn safety filtering and fallback placement.
9. The support edges follow the canonical column-chain/slab topology; reachability uses intact endpoints only.
