# UI and Controls Contract

**Feature**: `001-dynamic-demolition-sandbox`

This is a single-player desktop application. It exposes no network API, storage API or inter-process contract. The contract below defines the player-visible input and feedback surface that automated and manual validation must preserve.

## Input Contract

| Input | Active condition | Result |
|---|---|---|
| `W` | Gameplay active | Move forward relative to camera yaw. |
| `S` | Gameplay active | Move backward relative to camera yaw. |
| `A` | Gameplay active | Strafe left relative to camera yaw. |
| `D` | Gameplay active | Strafe right relative to camera yaw. |
| `Space` | Player grounded | Start one jump; ignored while airborne. |
| Hold right mouse button + drag | Gameplay active | Orbit third-person camera around player; release stops orbiting. |
| Left mouse button | Gameplay active and not orbiting | Pick the nearest visible segment under the cursor within `MAX_PICK_DISTANCE=60.0` world units and demolish it; empty, occluded or out-of-range space has no effect. |
| `Esc` | Any gameplay state | Exit the current game window cleanly. |

The cursor remains available for target selection. Left-click input received while the right button is held for camera orbit is ignored as a demolition command, preventing accidental destruction during camera adjustment.

## Camera Contract

- The player avatar remains visible in normal third-person view.
- Camera yaw follows right-button drag direction.
- Camera pitch is clamped so the camera cannot flip or look indefinitely through the ground.
- Camera movement does not change the player position.
- The same projected geometry used for visible target highlighting is used for left-click selection.

## Visual Feedback Contract

The HUD must provide:

- cumulative count of unique segment identities first made inactive in this session; a respawned segment can be demolished again but does not increment this number;
- highlight or target hint for the nearest visible selectable segment;
- respawn countdown when a destroyed segment is pending;
- basic controls hint.

The world must provide:

- a distinct target highlight before demolition;
- a visible state change when a segment is destroyed;
- falling debris for unsupported segments;
- a short flash, particle or camera-shake response;
- a visible push or slowdown response when debris contacts the player;
- a visible return of the segment after its respawn period.

## Command-Line Validation Contract

From the repository root:

```powershell
python game_3d.py
python game_3d.py --self-test
python -m unittest discover -s tests -v
```

- The default command opens the interactive game.
- `--self-test` runs deterministic, non-interactive rule checks and exits with success or failure.
- The unittest command runs the same pure-rule seams without requiring a visible game window.
