# Quickstart and Validation Guide

## Prerequisites

- Windows desktop with Python 3.14 available.
- Repository root: `C:\Users\user\OneDrive\桌面\python.sdd`.
- Existing virtual environment at `.venv` or an equivalent Python environment.

## Setup

```powershell
cd C:\Users\user\OneDrive\桌面\python.sdd
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

The feature keeps the existing `pygame-ce==2.5.8` dependency and adds no new package.

## Automated Validation

Run the following from the repository root:

```powershell
.\.venv\Scripts\python.exe -m py_compile game_3d.py
.\.venv\Scripts\python.exe game_3d.py --self-test
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Expected outcomes:

- `py_compile` exits successfully without creating a syntax error.
- `--self-test` verifies deterministic generation, projection／selection, movement／jump invariants, support reachability, one-time demolition counting, chunk streaming and respawn timers, then exits successfully.
- `unittest` reports all discovered tests passing without requiring a visible window.

## Validation Record

Date: 2026-08-27. Runtime: Python 3.14.0, `pygame-ce==2.5.8`, Windows desktop.

- Foundation, movement/jump/orbit/recovery, deterministic 3×3 streaming, selection,
  support cascade, debris/HUD/respawn and session lifecycle scenarios pass in 30
  headless unittest cases.
- The tests include 10 repeated debris contacts with no health/death state, 10
  stable-key demolitions across respawn, three streamed areas and a 900-frame
  representative exploration run with bounded loaded chunks/effects/debris.
- `game_3d.py --self-test` passes all core rule checks, including stable-key count
  idempotence and bounded collections.
- A 60-frame 1280×720 integrated update/HUD/render smoke run completed in 0.966 s
  (62.1 FPS) with 9 active chunks, 47 generated buildings and 9 loaded chunks.
- The project owner completed the manual desktop smoke flow on 2026-08-27 and
  reported no issues across launch, WASD movement, jumping, camera orbit, target
  selection, click/contact demolition, cascade/debris feedback, respawn,
  streaming/revisit and clean exit/relaunch. Exact stopwatch and 15-minute
  timestamps were not independently captured in this record.
- Post-review code validation fixed the transient debris-push overwrite and
  duplicate static-AABB scan; `py_compile`, `--self-test` and all 30 unittest
  cases pass after the changes.
- The five-person usability protocol below remains pending until five external
  testers can use a visible build.

## Final Traceability Review

The implementation covers FR-001–FR-017 through the session/player/camera model,
streamed chunk generator, segmented support graph, projected picking, contact
demolition, bounded debris/effects, respawn records, HUD and clean lifecycle
handlers. The automated scenarios cover SC-003–SC-008 and a representative
bounded exploration run for SC-009. The project-owner manual report now covers
the visible desktop flow for SC-001, SC-002 and SC-009, while SC-010 still needs
the five-person protocol below; the manual report is not claimed as an automated
substitute.

## Manual Smoke Test

1. Start a stopwatch immediately before `.\.venv\Scripts\python.exe game_3d.py`; pass SC-001 when the playable third-person scene appears within 60 seconds.
2. Confirm a third-person block avatar, a safe starting area and at least 30 varied neon low-poly buildings are available in the 3×3 active set; the spawn exclusion must not reduce the count below 30.
3. Hold right mouse and drag; confirm the camera orbits while the avatar remains visible.
4. Use W/A/S/D to move in all four directions. Press Space while grounded, then press it again in midair; confirm only the first press jumps.
5. Within the first two minutes, move the cursor over a visible building segment. Confirm the nearest target is highlighted, then left-click it and observe the segment state change, count increment and effects; complete the same movement, jump and camera checks before the two-minute mark for SC-002.
6. Walk into an intact segment. Confirm contact can demolish the contacted segment once, while the player remains controllable and does not repeatedly increment the count during one contact.
7. Destroy a lower support. Confirm unsupported upper segments begin falling within 120 simulation frames (2 seconds at 60 FPS) while supported segments stay in place; repeat debris contact 10 times and confirm it visibly pushes or slows the player without death, permanent lock or game over.
8. Move across at least three newly generated city areas. Confirm new buildings appear and the game remains responsive; return to a prior area and confirm its layout is stable.
9. Wait for a destroyed segment's approximately 30-second respawn. Confirm it returns in a supported state or waits until its support is restored, then can be demolished again.
10. Close with `Esc` and relaunch. Confirm the new session starts with a fresh city and reset demolition count.

## Failure / Boundary Checks

- Click empty space, an occluded segment or a segment more than 60 world units away: no target, no demolition, no count change.
- Hold Space in the air: no double jump.
- Keep colliding with one segment: no repeated count from one contact.
- Complete 10 valid click/contact demolitions: each stable target contributes at most once to the HUD count.
- Leave and revisit an area before the respawn period: the destroyed segment remains absent.
- Revisit after the respawn period: the original segment is present again.
- Fall below the recoverable world height: player returns to the last safe position.
- Run the game for at least 15 minutes while moving and demolishing: active area remains bounded and controllable.

## Five-Person Usability Validation (SC-010)

Run this after the integrated build is available and before sign-off:

1. Recruit five people who have not read the implementation documents. Test them one at a time using a fresh session.
2. Show each tester only the in-game HUD and controls hint; do not explain the key bindings or demolition rules.
3. Ask each tester to move in four directions, jump once, orbit the camera and demolish one building segment using the visible target feedback.
4. Ask each tester to identify what the demolition count and respawn countdown mean.
5. Record each tester as `pass` only if all requested actions and both HUD interpretations are completed without coaching. SC-010 passes when at least 4 of 5 testers pass.

Record the date, build revision, anonymized tester IDs, per-action results, coaching incidents and any confusing HUD wording below this protocol when T042 is executed.

## References

- Entity states and invariants: [data-model.md](./data-model.md)
- Keyboard, mouse and HUD behavior: [contracts/ui-controls.md](./contracts/ui-controls.md)
- Product acceptance scenarios: [spec.md](./spec.md)
