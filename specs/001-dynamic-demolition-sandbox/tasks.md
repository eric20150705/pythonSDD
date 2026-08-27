---

description: "Dependency-ordered implementation tasks for the Dynamic Demolition Sandbox"
---

# Tasks: Dynamic Demolition Sandbox

**Input**: Design documents from `specs/001-dynamic-demolition-sandbox/`

**Prerequisites**: [plan.md](./plan.md), [spec.md](./spec.md), [research.md](./research.md), [data-model.md](./data-model.md), [contracts/ui-controls.md](./contracts/ui-controls.md), [quickstart.md](./quickstart.md)

**Tests**: Automated tests are included because the project constitution and implementation plan require focused checks for collision, timing, support reachability, state transitions and deterministic generation. Tests for each story should be written before that story's implementation and confirmed to fail for the missing behavior.

**Organization**: Tasks are grouped by user story. User Story 1 is the first playable checkpoint; User Stories 2 and 3 complete the core demolition loop; User Stories 4 and 5 complete the full prototype.

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Establish an import-safe game entry point and a headless test harness without changing the existing learning exercises.

- [X] T001 Create the import-safe game entry point, constants section, `main()` stub and `--self-test` argument handling in `game_3d.py`.
- [X] T002 [P] Create the headless `unittest` harness, pygame cleanup fixture and reusable frame-advance helpers in `tests/test_game_3d.py`.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Build the shared coordinate, projection, rendering and session boundaries required by every user story.

**⚠️ CRITICAL**: No user story work can be considered complete until this phase is finished.

- [X] T003 [P] Add foundational projection, near-plane, cuboid geometry, session-invariant and headless-import tests in `tests/test_game_3d.py`, and run them once to confirm the missing foundation is detected.
- [X] T004 Implement 3D vector, cuboid, AABB and world-to-local geometry helpers in `game_3d.py`.
- [X] T005 Implement camera-space transforms, near-plane handling, perspective point projection and projected-face depth values in `game_3d.py`.
- [X] T006 Implement neon face shading, depth-sorted cuboid drawing and import-safe pygame surface helpers in `game_3d.py`.
- [X] T007 Implement the fixed 60 FPS session update boundary, bounded effect collection and clean interactive/headless initialization paths in `game_3d.py`.
- [X] T008 Run the foundational headless-import and geometry tests, confirm they fail before implementation and pass after the shared foundation is complete using `tests/test_game_3d.py` and `game_3d.py`.

**Checkpoint**: Projection helpers, render helpers, test harness and session boundaries are available; no story implementation should depend on opening a visible window during unit tests.

---

## Phase 3: User Story 1 - 探索城市與操控角色 (Priority: P1) 🎯 MVP

**Goal**: Deliver a visible third-person block avatar that can move relative to the camera, jump once from the ground, orbit the camera and recover safely.

**Independent Test**: Start at a safe ground position, use W/A/S/D to move in all four directions, press Space once while grounded and once while airborne, and hold right mouse while dragging; confirm the avatar remains visible, does not double-jump or pass through static geometry, and can recover from a fall.

### Tests for User Story 1

- [X] T009 [P] [US1] Add tests for camera-relative WASD movement, grounded jump, airborne Space rejection, camera orbit and safe recovery in `tests/test_game_3d.py`.

### Implementation for User Story 1

- [X] T010 [US1] Implement the block avatar state, position, velocity, grounded flag, last-safe position and gravity update in `game_3d.py`.
- [X] T011 [US1] Implement third-person camera follow, right-button orbit, yaw/pitch clamping and camera-relative movement vectors in `game_3d.py`.
- [X] T012 [US1] Implement player-versus-static-AABB movement resolution, ground detection, one-jump-only behavior and below-world recovery in `game_3d.py`.
- [X] T013 [US1] Wire keyboard, mouse-button and quit events into the fixed update loop and render the avatar with the camera in `game_3d.py`.
- [X] T014 [US1] Run the User Story 1 scenarios and record movement, jump, camera and recovery results in `specs/001-dynamic-demolition-sandbox/quickstart.md`.

**Checkpoint**: User Story 1 is independently playable and demonstrable before any city-generation or demolition work begins.

---

## Phase 4: User Story 2 - 在持續延伸的城市中探索 (Priority: P1)

**Goal**: Generate a stable, varied city around the player, stream new areas while moving and keep the start area safe.

**Independent Test**: Move through at least three new city areas, confirm each produces new varied buildings without a manual map load, return to a prior area and confirm its layout is stable and not duplicated.

### Tests for User Story 2

- [X] T015 [P] [US2] Add tests for deterministic chunk layouts, 4–6 buildings per chunk, aggregate active-world density of at least 30 after spawn exclusion, spawn safety, active-set bounds, new-area loading and no duplicate building IDs in `tests/test_game_3d.py`.

### Implementation for User Story 2

- [X] T016 [US2] Implement stable world-seed mixing, `CityChunk` identity and 32×32 chunk layout generation with 4–6 varied buildings plus deterministic legal fallback lots in `game_3d.py`.
- [X] T017 [US2] Implement `Building` and `BuildingSegment` geometry, stable segment IDs, floor/column layout and the canonical four-column-chain/slab support topology in `game_3d.py`.
- [X] T018 [US2] Implement the exact 3×3 `CityWorld` active set, one-pending-chunk swap bound (maximum 10 loaded), load/unload transitions, deterministic regeneration and bounded destruction overrides in `game_3d.py`.
- [X] T019 [US2] Integrate generated buildings with projection rendering, static collision bounds, an 8.0-unit clear spawn radius and aggregate active-world density enforcement of at least 30 buildings in `game_3d.py`.
- [X] T020 [US2] Run the User Story 2 streaming and revisit scenarios and record results, density observations and known limits in `specs/001-dynamic-demolition-sandbox/quickstart.md`.

**Checkpoint**: User Stories 1 and 2 both work: the player can explore a continuously extending city while the active world remains bounded.

---

## Phase 5: User Story 3 - 破壞大樓並觸發連鎖坍塌 (Priority: P1)

**Goal**: Let the player select a visible building segment with the cursor or contact it, then trigger one-time demolition and support-driven cascading collapse.

**Independent Test**: Click one visible segment, collide with another, destroy a lower support and confirm the selected/contacted segment is counted once, unsupported upper segments fall, and supported segments remain stable.

### Tests for User Story 3

- [X] T021 [P] [US3] Add tests for nearest-visible-segment picking, empty/occluded/out-of-range clicks, 15-frame collision demolition cooldown, canonical support reachability and cascade results within 120 frames, plus 10 consecutive valid demolitions with one-time stable-key count increments across respawn and chunk reload in `tests/test_game_3d.py`.

### Implementation for User Story 3

- [X] T022 [US3] Implement projected-face hit testing, nearest-depth selection, `MAX_PICK_DISTANCE=60.0` filtering and target highlighting in `game_3d.py`.
- [X] T023 [US3] Implement `demolish_segment()` with click/contact causes, intact-state guards, `CONTACT_COOLDOWN_FRAMES=15` per-contact cooldowns and one-time stable-key demolition counting that survives respawn and chunk reload in `game_3d.py`.
- [X] T024 [US3] Implement the canonical support graph (`COLUMN(0,c)->BASE`, upper columns to the same lower column, slabs to four same-floor columns) and transition newly unsupported intact segments into FALLING in `game_3d.py`.
- [X] T025 [US3] Wire left-click selection and player-contact demolition into the event, collision and world-update stages in `game_3d.py`.
- [X] T026 [US3] Run the User Story 3 click, collision, support and cascade scenarios, verify unsupported segments begin falling within 120 frames and the 10-demolition count rule, and record results in `specs/001-dynamic-demolition-sandbox/quickstart.md`.

**Checkpoint**: User Stories 1–3 form the core playable demolition loop: move, aim, break and watch unsupported building sections collapse.

---

## Phase 6: User Story 4 - 感受坍塌回饋並等待重建 (Priority: P2)

**Goal**: Add falling debris, visual feedback, player push/slow behavior, HUD status and independently timed segment respawn.

**Independent Test**: Destroy a support, observe falling debris and feedback, touch debris without dying, wait for the approximately 30-second segment respawn and demolish the restored segment again.

### Tests for User Story 4

- [X] T027 [P] [US4] Add tests for `DEBRIS_LIFETIME_FRAMES=180`, `DEBRIS_SLOW_FRAMES=30`, `MAX_EFFECT_LIFETIME_FRAMES=45`, bounded debris/effect collections, effect expiry, player push/slow without damage, 1,800-frame respawn timing, unsupported pending respawn and chunk reload state in `tests/test_game_3d.py`.

### Implementation for User Story 4

- [X] T028 [US4] Implement `Debris` with `DEBRIS_LIFETIME_FRAMES=180` and bounded short-lived `Effect` records for flash, particle and camera-shake feedback with fixed-frame gravity and cleanup in `game_3d.py`.
- [X] T029 [US4] Implement debris-player proximity response that pushes or slows the player for at most `DEBRIS_SLOW_FRAMES=30` without health, death or permanent collision state in `game_3d.py`.
- [X] T030 [US4] Implement per-segment respawn records, 1,800-frame countdowns, supported bottom-up restoration, PENDING_RESPAWN ordering and reapplication after chunk reload; allow restored segments to be demolished again without increasing the stable-key unique count in `game_3d.py`.
- [X] T031 [US4] Implement HUD rendering for demolition count, current target, respawn countdown, controls and destruction feedback in `game_3d.py`.
- [X] T032 [US4] Run the User Story 4 debris, HUD and respawn scenarios, repeat debris contact 10 times with zero death/permanent lock, and record timing tolerance and known visual limits in `specs/001-dynamic-demolition-sandbox/quickstart.md`.

**Checkpoint**: Destruction is readable, harmless to the player, repeatable after respawn and supported by visible HUD state.

---

## Phase 7: User Story 5 - 以自由沙盒方式持續遊玩 (Priority: P2)

**Goal**: Finalize the no-win sandbox session, safe recovery, clean exit and fresh-session reset behavior.

**Independent Test**: Demolish multiple buildings, continue exploring without a win or loss screen, recover after falling, exit with Esc and relaunch with a fresh city and reset count.

### Tests for User Story 5

- [X] T033 [P] [US5] Add tests for no forced win/game-over state, last-safe-position recovery, clean session initialization and reset of world seed/count in `tests/test_game_3d.py`.

### Implementation for User Story 5

- [X] T034 [US5] Implement session bootstrap, fresh world seed creation, reset of demolition statistics and explicit absence of win/game-over transitions in `game_3d.py`.
- [X] T035 [US5] Integrate `RECOVERY_HEIGHT=-20.0` below-world recovery, QUIT/Esc handling, input release cleanup and camera reset into the final game lifecycle in `game_3d.py`.
- [X] T036 [US5] Run the User Story 5 long-session, fall-recovery, exit and relaunch scenarios and record results in `specs/001-dynamic-demolition-sandbox/quickstart.md`.

**Checkpoint**: The complete single-player sandbox can be explored, demolished, recovered from and restarted without persistent progression requirements.

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Verify the integrated prototype, document the final controls and protect the project constitution invariants.

- [X] T037 [P] Update `README.md` to match the implemented third-person controls, dynamic-city behavior, self-test command, unittest command and v1 exclusions.
- [X] T038 [P] Run `py_compile` for `game_3d.py`, `game_3d.py --self-test` and `unittest discover -s tests -v`; fix failures in `game_3d.py` or `tests/test_game_3d.py` before sign-off.
- [X] T039 Run the complete manual flow from `specs/001-dynamic-demolition-sandbox/quickstart.md`, including the ≤60-second launch check, ≤2-minute first-use flow, 10-demolition count check and 15-minute bounded-world check, and record actual results and limitations in `specs/001-dynamic-demolition-sandbox/quickstart.md`.
- [X] T040 Enforce active-chunk, debris-lifetime and effect-count bounds, verify key-only demolition history stays out of render/update geometry paths, and inspect hot paths for the 60 FPS target in `game_3d.py`.
- [X] T041 Perform the final constitution and requirement traceability review against `specs/001-dynamic-demolition-sandbox/plan.md`, `specs/001-dynamic-demolition-sandbox/spec.md`, `specs/001-dynamic-demolition-sandbox/data-model.md`, `specs/001-dynamic-demolition-sandbox/contracts/ui-controls.md` and `specs/001-dynamic-demolition-sandbox/quickstart.md`.
- [ ] T042 Conduct the five-person SC-010 usability validation using only the HUD controls hint, record per-tester action/HUD interpretation results and confirm at least 4 of 5 testers pass in `specs/001-dynamic-demolition-sandbox/quickstart.md`.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 — Setup**: T001 and T002 have no implementation dependency and can run in parallel.
- **Phase 2 — Foundational**: T003–T008 depend on the setup entry point/test harness; this phase blocks all user-story completion.
- **Phase 3 — User Story 1**: T009–T014 depend on Phase 2 and produce the first playable checkpoint.
- **Phase 4 — User Story 2**: T015–T020 depend on Phase 2 and integrate with the completed player/camera slice from Phase 3.
- **Phase 5 — User Story 3**: T021–T026 depend on the city segment model and player collision from Phases 3–4.
- **Phase 6 — User Story 4**: T027–T032 depend on demolition and support transitions from Phase 5.
- **Phase 7 — User Story 5**: T033–T036 depend on the integrated behavior from Phases 3–6.
- **Phase 8 — Polish**: T037–T042 depend on all desired user stories and their focused tests being complete; T042 follows T039 because both append validation results to `quickstart.md`.

### User Story Dependencies

```text
Foundational
    ↓
US1: player + camera + jump + recovery
    ↓
US2: deterministic streamed city + building segments
    ↓
US3: picking + contact demolition + support cascade
    ↓
US4: debris + feedback + respawn
    ↓
US5: sandbox lifecycle + restart
    ↓
Polish and final validation
```

The stories are ordered by their usable dependency in this single-file prototype even though US1, US2 and US3 are all P1 in the product specification. The test portions of later stories can be prepared earlier, but their integrated implementation cannot be accepted until the preceding story exposes the required state.

### Requirement Coverage

| Requirements | Tasks |
|---|---|
| FR-001–FR-004, SC-001–SC-002 | T001–T014 |
| FR-005–FR-007, SC-003–SC-004 | T015–T020 |
| FR-008–FR-010, FR-012, SC-005–SC-006 | T021–T026 |
| FR-011, FR-013–FR-015, SC-007–SC-008 | T027–T032 |
| FR-016–FR-017, SC-009 | T033–T036 |
| SC-010 | T039, T042 |
| Cross-cutting quality, performance and documentation | T037–T041 |

## Parallel Execution Examples

### Setup and Foundation

```text
T001 Create game_3d.py entry skeleton
T002 Create tests/test_game_3d.py headless harness

After T002:
T003 writes tests/test_game_3d.py checks in parallel with source implementation
T004/T005/T006/T007 extend game_3d.py in sequence
T008 runs the completed foundational checks
```

### User Story 1

```text
T009 [US1] Write player/camera tests in tests/test_game_3d.py
T010 [US1] Implement player state in game_3d.py
```

T009 can be prepared in parallel with T010. T011–T013 then remain sequential because they extend the same game loop and player/camera responsibilities.

### User Story 2

```text
T015 [US2] Write generation/streaming tests in tests/test_game_3d.py
T016 [US2] Implement chunk/building generation in game_3d.py
```

T015 can be prepared in parallel with T016. T017–T019 must follow the generation interfaces in T016 and remain sequential in `game_3d.py`.

### User Story 3

```text
T021 [US3] Write picking/cascade tests in tests/test_game_3d.py
T022 [US3] Implement projected picking in game_3d.py
```

T021 can be prepared in parallel with T022. T023–T025 are ordered because demolition state must exist before cascade evaluation is wired into the loop.

### User Stories 4 and 5

```text
T027 [US4] Write debris/respawn tests in tests/test_game_3d.py
T028 [US4] Implement debris/effects in game_3d.py

T033 [US5] Write lifecycle tests in tests/test_game_3d.py
T034 [US5] Implement session lifecycle in game_3d.py
```

Within each story, the test task can be prepared in parallel with the corresponding source task; all integrated story tasks remain ordered because they share `game_3d.py`.

### Final Polish

```text
T037 Update README.md
T038 Run automated validation for game_3d.py and tests/test_game_3d.py
```

T037 and T038 touch independent outputs and can run in parallel after the final behavior is stable. T039 and T042 both update `quickstart.md` and therefore run sequentially; T040–T041 complete the remaining sign-off review.

## Implementation Strategy

### MVP Checkpoint

1. Complete T001–T008.
2. Complete T009–T013 for User Story 1.
3. Run T014 and stop for a playable movement/camera/jump review.

This checkpoint proves the project can launch, render a 3D scene and support the core player controls before city complexity is added.

### Core Feature Delivery

1. Add User Story 2 and validate streamed city generation.
2. Add User Story 3 and validate click/contact demolition plus support cascade.
3. Treat T026 as the core demolition demo milestone.

### Full Prototype Delivery

1. Add User Story 4 for debris, HUD, effects and respawn.
2. Add User Story 5 for sandbox lifecycle and recovery.
3. Complete T037–T042 and run the full quickstart checklist, including the five-person usability protocol.

Every checkpoint must preserve the earlier story behavior. The existing `day1/` and `day2/` exercises remain untouched throughout.

## Notes

- Every implementation task names an exact file path and uses the required checkbox/ID format.
- `[P]` is used only for work that can be prepared independently in a different file or output.
- `[US1]` through `[US5]` map directly to the five user stories in `spec.md`.
- No `contracts/` test directory is required because the application exposes a user-facing keyboard/mouse contract rather than a network or library API; UI contract checks are covered in `tests/test_game_3d.py` and `quickstart.md`.
- Existing `day1/` and `day2/` code is intentionally outside the task scope.
