"""Headless tests for the NEON CITY pure gameplay seams."""

from __future__ import annotations

import os
import unittest
from unittest.mock import patch

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame

import game_3d


class PygameTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        pygame.init()

    @classmethod
    def tearDownClass(cls) -> None:
        pygame.quit()

    @staticmethod
    def make_session(seed: int = 9001) -> game_3d.SessionState:
        """Create a deterministic feature-session fixture."""

        return game_3d.create_session(world_seed=seed)

    @staticmethod
    def make_segment_building(
        building_id: str = "fixture:0:0:0",
        origin: game_3d.Vector3 | None = None,
    ) -> game_3d.Building:
        """Create a small deterministic building used by interaction tests."""

        return game_3d.Building.create(
            building_id,
            game_3d.Vector3(0, 0, 18) if origin is None else origin,
            6,
            6,
            4,
            (80, 200, 240),
        )

    @staticmethod
    def make_surface(size: tuple[int, int] = (800, 600)) -> pygame.Surface:
        """Create a display-independent surface for render assertions."""

        return game_3d.create_render_surface(size)

    @staticmethod
    def segment_cursor(
        session: game_3d.SessionState,
        building: game_3d.Building,
        segment: game_3d.BuildingSegment,
        screen_size: tuple[int, int] = (800, 600),
    ) -> tuple[int, int]:
        target = session.player.position + session.camera.target_offset
        projected = game_3d.project_point(
            segment.world_position(building.origin),
            session.camera,
            target,
            screen_size,
        )
        if projected is None:
            raise AssertionError("fixture segment must be projectable")
        return round(projected[0]), round(projected[1])

    @staticmethod
    def advance_session(
        session: game_3d.SessionState,
        frames: int,
        movement: game_3d.Vector3 | None = None,
    ) -> None:
        for _ in range(frames):
            game_3d.update_session_core(
                session,
                game_3d.Vector3() if movement is None else movement,
            )

    @staticmethod
    def install_building(
        session: game_3d.SessionState,
        building: game_3d.Building,
        coord: tuple[int, int] = (0, 0),
    ) -> None:
        session.world.active_chunks[coord].buildings = [building]
        session.world.visible_chunks[coord] = session.world.active_chunks[coord]


class FoundationTests(PygameTestCase):
    def test_import_exposes_core_runtime_constants(self) -> None:
        self.assertEqual(game_3d.FPS, 60)
        self.assertEqual(game_3d.SCREEN_SIZE, (1280, 720))

    def test_vector_and_aabb_helpers_are_available(self) -> None:
        point = game_3d.Vector3(1, 2, 3)
        box = game_3d.AABB.from_center_size(point, game_3d.Vector3(2, 2, 2))
        self.assertTrue(box.contains(point))
        self.assertEqual(game_3d.world_to_local(point, point), game_3d.Vector3(0, 0, 0))

    def test_projection_rejects_points_behind_near_plane(self) -> None:
        camera = game_3d.Camera()
        target = game_3d.Vector3(0, 1, 0)
        behind = camera.position(target) + game_3d.Vector3(0, 0, -1)
        self.assertIsNone(game_3d.project_point(behind, camera, target, (800, 600)))

    def test_projection_returns_screen_point_for_visible_point(self) -> None:
        camera = game_3d.Camera()
        target = game_3d.Vector3(0, 1, 0)
        visible = camera.position(target) + camera.forward(target) * 10
        projected = game_3d.project_point(visible, camera, target, (800, 600))
        self.assertIsNotNone(projected)
        self.assertAlmostEqual(projected[0], 400, delta=2)
        self.assertAlmostEqual(projected[1], 300, delta=2)

    def test_session_effect_collection_is_bounded_and_expires(self) -> None:
        session = game_3d.SessionState(world_seed=7)
        short = session.add_effect("FLASH", game_3d.Vector3(), lifetime=2)
        session.advance_frame()
        session.advance_frame()
        self.assertNotIn(short, session.effects)
        for _ in range(game_3d.MAX_EFFECTS + 5):
            session.add_effect("PARTICLE", game_3d.Vector3())
        self.assertLessEqual(len(session.effects), game_3d.MAX_EFFECTS)
        self.assertTrue(all(effect.remaining_frames > 0 for effect in session.effects))


class PlayerCameraTests(PygameTestCase):
    def test_camera_relative_direction_follows_yaw(self) -> None:
        camera = game_3d.Camera(yaw=0.0)
        forward = game_3d.camera_relative_movement(camera, forward=1.0, strafe=0.0)
        self.assertAlmostEqual(forward.x, 0.0, delta=0.001)
        self.assertAlmostEqual(forward.z, 1.0, delta=0.001)
        camera.yaw = 3.14159265 / 2.0
        turned = game_3d.camera_relative_movement(camera, forward=1.0, strafe=0.0)
        self.assertAlmostEqual(turned.x, 1.0, delta=0.001)
        self.assertAlmostEqual(turned.z, 0.0, delta=0.001)

    def test_jump_is_allowed_only_from_ground(self) -> None:
        player = game_3d.Player(game_3d.Vector3(0, game_3d.PLAYER_HALF_HEIGHT, 0))
        self.assertTrue(player.try_jump())
        self.assertFalse(player.grounded)
        self.assertGreater(player.velocity.y, 0.0)
        self.assertFalse(player.try_jump())

    def test_camera_orbit_changes_yaw_and_clamps_pitch(self) -> None:
        camera = game_3d.Camera()
        old_yaw = camera.yaw
        camera.orbit(40, 100000)
        self.assertNotEqual(camera.yaw, old_yaw)
        self.assertLessEqual(camera.pitch, game_3d.CAMERA_PITCH_MAX)
        camera.orbit(0, -100000)
        self.assertGreaterEqual(camera.pitch, game_3d.CAMERA_PITCH_MIN)

    def test_player_resolves_static_collision_and_does_not_pass_through(self) -> None:
        player = game_3d.Player(game_3d.Vector3(0, game_3d.PLAYER_HALF_HEIGHT, 0))
        wall = game_3d.AABB.from_center_size(
            game_3d.Vector3(1.2, 1.0, 0), game_3d.Vector3(1, 2, 3)
        )
        for frame in range(30):
            game_3d.update_player(player, game_3d.Vector3(1, 0, 0), [wall], frame)
        self.assertLessEqual(player.aabb().maximum.x, wall.minimum.x + 0.001)

    def test_player_recovers_to_last_safe_position_below_world(self) -> None:
        safe = game_3d.Vector3(3, game_3d.PLAYER_HALF_HEIGHT, 4)
        player = game_3d.Player(safe)
        player.position = game_3d.Vector3(30, game_3d.RECOVERY_HEIGHT - 1, 30)
        player.grounded = False
        game_3d.recover_player_if_needed(player)
        self.assertEqual(player.position, safe)
        self.assertTrue(player.grounded)

    def test_foundation_session_can_update_and_render_without_display(self) -> None:
        session = game_3d.SessionState(world_seed=12)
        surface = game_3d.create_render_surface((800, 600))
        game_3d.update_session_core(session, game_3d.Vector3(0, 0, 1))
        game_3d.render_basic_scene(surface, session)
        self.assertEqual(session.frame, 1)
        self.assertNotEqual(surface.get_at((400, 300))[:3], (8, 10, 24))


class CityWorldTests(PygameTestCase):
    def test_same_seed_and_chunk_coordinate_reproduce_the_same_layout(self) -> None:
        first = game_3d.CityWorld(1234)
        second = game_3d.CityWorld(1234)
        first.ensure_active(game_3d.Vector3(0, game_3d.PLAYER_HALF_HEIGHT, 0))
        second.ensure_active(game_3d.Vector3(0, game_3d.PLAYER_HALF_HEIGHT, 0))
        first_layout = [
            (building.building_id, tuple(building.origin), building.floor_count)
            for building in first.all_buildings()
        ]
        second_layout = [
            (building.building_id, tuple(building.origin), building.floor_count)
            for building in second.all_buildings()
        ]
        self.assertEqual(first_layout, second_layout)

    def test_active_world_has_bounded_chunks_and_at_least_thirty_buildings(self) -> None:
        world = game_3d.CityWorld(8)
        world.ensure_active(game_3d.Vector3(0, game_3d.PLAYER_HALF_HEIGHT, 0))
        self.assertEqual(len(world.active_chunks), 9)
        self.assertLessEqual(world.loaded_chunk_count, game_3d.MAX_LOADED_CHUNKS)
        self.assertGreaterEqual(len(world.all_buildings()), game_3d.MIN_ACTIVE_BUILDINGS)
        self.assertLessEqual(len(world.all_buildings()), game_3d.MAX_ACTIVE_BUILDINGS)
        self.assertGreater(len({building.floor_count for building in world.all_buildings()}), 1)
        self.assertGreater(len({building.color for building in world.all_buildings()}), 1)
        self.assertTrue(
            all(
                game_3d.BUILDINGS_PER_CHUNK_MIN
                <= len(chunk.buildings)
                <= game_3d.BUILDINGS_PER_CHUNK_MAX
                for chunk in world.active_chunks.values()
            )
        )

    def test_spawn_radius_is_clear_and_building_ids_are_unique(self) -> None:
        world = game_3d.CityWorld(99)
        world.ensure_active(game_3d.Vector3(0, game_3d.PLAYER_HALF_HEIGHT, 0))
        ids = [building.building_id for building in world.all_buildings()]
        self.assertEqual(len(ids), len(set(ids)))
        for building in world.all_buildings():
            self.assertGreaterEqual(building.distance_to_xz(game_3d.Vector3()), game_3d.SPAWN_SAFE_RADIUS)

    def test_streaming_loads_new_area_and_revisiting_regenerates_stable_layout(self) -> None:
        world = game_3d.CityWorld(55)
        origin = game_3d.Vector3(0, game_3d.PLAYER_HALF_HEIGHT, 0)
        world.ensure_active(origin)
        original = world.chunk_layout((0, 0))
        original_ids = {building.building_id for building in world.all_buildings()}
        for position, expected_chunk in (
            (game_3d.Vector3(game_3d.CHUNK_SIZE * 2.1, game_3d.PLAYER_HALF_HEIGHT, 0), (2, 0)),
            (game_3d.Vector3(0, game_3d.PLAYER_HALF_HEIGHT, game_3d.CHUNK_SIZE * 2.1), (0, 2)),
            (game_3d.Vector3(-game_3d.CHUNK_SIZE * 2.1, game_3d.PLAYER_HALF_HEIGHT, 0), (-2, 0)),
        ):
            world.ensure_active(position)
            self.assertEqual(len(world.active_chunks), 9)
            self.assertLessEqual(world.loaded_chunk_count, game_3d.MAX_LOADED_CHUNKS)
            self.assertIn(expected_chunk, world.active_chunks)
            self.assertTrue(
                {building.building_id for building in world.active_chunks[expected_chunk].buildings}
                .isdisjoint(original_ids)
            )
        world.ensure_active(origin)
        self.assertEqual(world.chunk_layout((0, 0)), original)


class DemolitionTests(PygameTestCase):
    def make_building(self) -> game_3d.Building:
        return game_3d.Building.create(
            "test:0:0:0",
            game_3d.Vector3(0, 0, 18),
            6,
            6,
            4,
            (80, 200, 240),
        )

    def test_picking_chooses_nearest_visible_segment_and_rejects_empty_or_far_clicks(self) -> None:
        building = self.make_building()
        camera = game_3d.Camera()
        target = game_3d.Vector3(0, 1, 0)
        player_position = game_3d.Vector3(0, game_3d.PLAYER_HALF_HEIGHT, 0)
        segment = building.segment((building.building_id, 0, 0, "column"))
        self.assertIsNotNone(segment)
        projected = game_3d.project_point(
            segment.world_position(building.origin), camera, target, (800, 600)
        )
        self.assertIsNotNone(projected)
        picked = game_3d.pick_nearest_segment(
            (projected[0], projected[1]),
            camera,
            target,
            player_position,
            [(building, segment)],
            (800, 600),
        )
        self.assertEqual(picked[1].segment_id, segment.segment_id)
        self.assertIsNone(
            game_3d.pick_nearest_segment(
                (10, 10), camera, target, player_position, [(building, segment)], (800, 600)
            )
        )

        far_building = game_3d.Building.create(
            "far:0:0:0", game_3d.Vector3(0, 0, 100), 6, 6, 4, (80, 200, 240)
        )
        far_segment = far_building.segment((far_building.building_id, 0, 0, "column"))
        far_projected = game_3d.project_point(
            far_segment.world_position(far_building.origin), camera, target, (800, 600)
        )
        self.assertIsNone(
            game_3d.pick_nearest_segment(
                (far_projected[0], far_projected[1]),
                camera,
                target,
                player_position,
                [(far_building, far_segment)],
                (800, 600),
            )
        )

    def test_support_cascade_keeps_other_column_chains_stable(self) -> None:
        session = game_3d.SessionState(world_seed=10)
        building = self.make_building()
        target_id = (building.building_id, 1, 0, "column")
        target = building.segment(target_id)
        changed = game_3d.demolish_segment(session, building, target, cause="click")
        changed_ids = {segment.segment_id for segment in changed}
        self.assertIn(target_id, changed_ids)
        self.assertEqual(building.segment((building.building_id, 2, 0, "column")).status, game_3d.FALLING)
        self.assertEqual(building.segment((building.building_id, 2, 1, "column")).status, game_3d.INTACT)
        self.assertEqual(session.destroyed_count, len(changed_ids))
        self.assertTrue(
            {"FLASH", "PARTICLE", "CAMERA_SHAKE"}
            <= {effect.kind for effect in session.effects}
        )
        self.assertNotEqual(game_3d.camera_shake_offset(session), game_3d.Vector3())

    def test_contact_cooldown_and_count_are_idempotent(self) -> None:
        player = game_3d.Player(game_3d.Vector3(0, game_3d.PLAYER_HALF_HEIGHT, 0))
        key = ("building", 0, 0, "column")
        self.assertTrue(game_3d.contact_is_ready(player, key, 0))
        self.assertFalse(game_3d.contact_is_ready(player, key, 1))
        self.assertFalse(game_3d.contact_is_ready(player, key, game_3d.CONTACT_COOLDOWN_FRAMES - 1))
        self.assertTrue(game_3d.contact_is_ready(player, key, game_3d.CONTACT_COOLDOWN_FRAMES))

        session = game_3d.SessionState(world_seed=11)
        building = self.make_building()
        target = building.segment((building.building_id, 0, 1, "column"))
        first = game_3d.demolish_segment(session, building, target, cause="contact", player=player)
        second = game_3d.demolish_segment(session, building, target, cause="contact", player=player)
        self.assertTrue(first)
        self.assertFalse(second)
        self.assertEqual(session.destroyed_count, len({item.segment_id for item in first}))

    def test_mouse_event_wires_pull_demolition_and_ignores_orbit_clicks(self) -> None:
        session = game_3d.SessionState(world_seed=21)
        building = self.make_building()
        session.world.active_chunks[(0, 0)].buildings = [building]
        segment = building.segment((building.building_id, 0, 0, "column"))
        target = session.player.position + session.camera.target_offset
        projected = game_3d.project_point(
            segment.world_position(building.origin), session.camera, target, (800, 600)
        )
        orbit_event = pygame.event.Event(pygame.MOUSEBUTTONDOWN, {"button": 3, "pos": (0, 0)})
        game_3d.handle_game_event(session, orbit_event, (800, 600))
        pull_down = pygame.event.Event(
            pygame.MOUSEBUTTONDOWN,
            {"button": 1, "pos": (projected[0], projected[1])},
        )
        game_3d.handle_game_event(session, pull_down, (800, 600))
        self.assertEqual(session.destroyed_count, 0)
        game_3d.handle_game_event(
            session,
            pygame.event.Event(pygame.MOUSEBUTTONUP, {"button": 3, "pos": (0, 0)}),
            (800, 600),
        )
        game_3d.handle_game_event(
            session,
            pygame.event.Event(
                pygame.MOUSEBUTTONDOWN,
                {"button": 1, "pos": (projected[0], projected[1])},
            ),
            (800, 600),
        )
        game_3d.handle_game_event(
            session,
            pygame.event.Event(
                pygame.MOUSEMOTION,
                {"pos": (projected[0] + 30, projected[1]), "rel": (30, 0)},
            ),
            (800, 600),
        )
        game_3d.handle_game_event(
            session,
            pygame.event.Event(
                pygame.MOUSEBUTTONUP,
                {"button": 1, "pos": (projected[0] + 30, projected[1])},
            ),
            (800, 600),
        )
        self.assertIsNotNone(session.pull_action)
        self.assertEqual(session.pull_action.phase, game_3d.PULL_ANIMATING)
        for _ in range(game_3d.PULL_ANIMATION_FRAMES):
            game_3d.update_gameplay(session, game_3d.Vector3())
        self.assertGreaterEqual(session.destroyed_count, 1)
        self.assertEqual(segment.status, game_3d.FALLING)

    def test_ten_valid_demolitions_count_each_key_once_across_respawn(self) -> None:
        session = game_3d.SessionState(world_seed=22)
        building = self.make_building()
        targets = [
            building.segment((building.building_id, floor, -1, "slab"))
            for floor in range(4)
        ]
        targets.extend(
            building.segment((building.building_id, 3, column, "column"))
            for column in range(4)
        )
        targets.extend(
            building.segment((building.building_id, 2, column, "column"))
            for column in (0, 1)
        )
        self.assertTrue(all(target is not None for target in targets))
        for target in targets:
            self.assertTrue(game_3d.demolish_segment(session, building, target))
        self.assertEqual(session.destroyed_count, 10)
        self.assertEqual(len(session.counted_segment_keys), 10)

        session.frame = game_3d.RESPAWN_FRAMES
        game_3d.update_respawns_for_building(session, building)
        self.assertTrue(all(target.status == game_3d.INTACT for target in targets))
        for target in targets:
            game_3d.demolish_segment(session, building, target)
        self.assertEqual(session.destroyed_count, 10)


class DebrisRespawnTests(PygameTestCase):
    def make_building(self) -> game_3d.Building:
        return game_3d.Building.create(
            "respawn:0:0:0",
            game_3d.Vector3(0, 0, 18),
            6,
            6,
            4,
            (80, 200, 240),
        )

    def test_debris_has_fixed_lifetime_and_pushes_without_damage(self) -> None:
        debris = game_3d.Debris(("segment",), game_3d.Vector3(0, 1, 0))
        start_y = debris.position.y
        debris.update()
        self.assertLess(debris.position.y, start_y)
        debris.remaining_frames = 1
        debris.update()
        self.assertEqual(debris.remaining_frames, 0)

        player = game_3d.Player(game_3d.Vector3(0, game_3d.PLAYER_HALF_HEIGHT, 0))
        debris = game_3d.Debris(("segment",), game_3d.Vector3(0, 1, 0), push_radius=2.0)
        self.assertTrue(game_3d.apply_debris_contact(player, debris, 10))
        self.assertGreater(player.velocity.length_squared(), 0.0)
        self.assertEqual(player.slow_until_frame, 10 + game_3d.DEBRIS_SLOW_FRAMES)
        self.assertFalse(hasattr(player, "health"))

        pushed_player = game_3d.Player(game_3d.Vector3(0, game_3d.PLAYER_HALF_HEIGHT, 0))
        pushed_debris = game_3d.Debris(("pushed",), game_3d.Vector3(-1, 1, 0), push_radius=2.0)
        game_3d.apply_debris_contact(pushed_player, pushed_debris, 10)
        game_3d.update_player(pushed_player, game_3d.Vector3(), [], 11)
        self.assertGreater(pushed_player.position.x, 0.0)

        session = game_3d.SessionState(world_seed=30)
        for _ in range(game_3d.MAX_DEBRIS + 10):
            session.add_debris(game_3d.Debris(("bounded",), game_3d.Vector3()))
        self.assertLessEqual(len(session.debris), game_3d.MAX_DEBRIS)
        for _ in range(game_3d.DEBRIS_LIFETIME_FRAMES):
            session.advance_frame()
            game_3d.update_debris(session)
        self.assertEqual(session.debris, [])

        repeated_player = game_3d.Player(game_3d.Vector3(0, game_3d.PLAYER_HALF_HEIGHT, 0))
        repeated_debris = game_3d.Debris(("repeated",), game_3d.Vector3(0, 1, 0))
        for frame in range(10):
            self.assertTrue(game_3d.apply_debris_contact(repeated_player, repeated_debris, frame))
            self.assertLessEqual(
                repeated_player.slow_until_frame - frame,
                game_3d.DEBRIS_SLOW_FRAMES,
            )
        self.assertFalse(hasattr(repeated_player, "health"))

    def test_respawn_waits_for_frame_and_restores_bottom_up(self) -> None:
        session = game_3d.SessionState(world_seed=31)
        building = self.make_building()
        session.world.active_chunks[(0, 0)].buildings = [building]
        target = building.segment((building.building_id, 0, 0, "column"))
        changed = game_3d.demolish_segment(session, building, target)
        self.assertTrue(changed)
        for _ in range(game_3d.RESPAWN_FRAMES - 1):
            session.advance_frame()
            game_3d.update_respawns(session)
        self.assertNotEqual(target.status, game_3d.INTACT)
        session.advance_frame()
        game_3d.update_respawns(session)
        self.assertEqual(target.status, game_3d.INTACT)
        self.assertNotIn(target.segment_id, session.respawn_overrides)
        self.assertEqual(session.destroyed_count, len(session.counted_segment_keys))

    def test_unsupported_ready_segment_becomes_pending_until_support_returns(self) -> None:
        session = game_3d.SessionState(world_seed=32)
        building = self.make_building()
        lower = building.segment((building.building_id, 0, 0, "column"))
        upper = building.segment((building.building_id, 1, 0, "column"))
        lower.status = game_3d.ABSENT
        upper.status = game_3d.ABSENT
        session.respawn_overrides[lower.segment_id] = game_3d.RespawnRecord(
            lower.segment_id, 10, (0, 0), 0
        )
        session.respawn_overrides[upper.segment_id] = game_3d.RespawnRecord(
            upper.segment_id, 0, (0, 0), 0
        )
        game_3d.update_respawns_for_building(session, building)
        self.assertEqual(upper.status, game_3d.PENDING_RESPAWN)
        session.frame = 10
        game_3d.update_respawns_for_building(session, building)
        self.assertEqual(lower.status, game_3d.INTACT)
        self.assertEqual(upper.status, game_3d.INTACT)

    def test_chunk_reload_reapplies_destroyed_state_and_counted_identity(self) -> None:
        session = game_3d.SessionState(world_seed=33)
        building = session.world.active_chunks[(0, 0)].buildings[0]
        target = building.segment((building.building_id, 0, 1, "column"))
        changed = game_3d.demolish_segment(session, building, target)
        expected_count = len({item.segment_id for item in changed})
        self.assertEqual(session.destroyed_count, expected_count)
        session.frame = 5
        session.world.ensure_active(game_3d.Vector3(game_3d.CHUNK_SIZE * 3, 0, 0), session.frame)
        session.world.ensure_active(game_3d.Vector3(0, 0, 0), session.frame)
        reloaded = session.world.find_segment(target.segment_id)
        self.assertIsNotNone(reloaded)
        self.assertTrue(reloaded[1].counted)
        self.assertEqual(reloaded[1].status, game_3d.ABSENT)


class HUDTests(PygameTestCase):
    def test_hud_mirrors_count_target_and_respawn_state(self) -> None:
        session = game_3d.SessionState(world_seed=44)
        surface = game_3d.create_render_surface((800, 600))
        picked = game_3d.update_hud(session, (400, 300), surface.get_size())
        game_3d.draw_hud(surface, session)
        self.assertEqual(session.hud.destroyed_count, session.destroyed_count)
        self.assertEqual(session.hud.target_segment, None if picked is None else picked[1].segment_id)
        self.assertIn("WASD", session.hud.control_hint)

    def test_respawn_countdown_is_visible_as_seconds(self) -> None:
        session = game_3d.SessionState(world_seed=45)
        building = session.world.active_chunks[(0, 0)].buildings[0]
        segment = building.segment((building.building_id, 0, 0, "column"))
        game_3d.demolish_segment(session, building, segment)
        game_3d.update_hud(session, (0, 0), (800, 600))
        self.assertEqual(session.hud.respawn_remaining, 30)


class SessionLifecycleTests(PygameTestCase):
    def test_sandbox_has_no_forced_win_or_game_over_transition(self) -> None:
        session = game_3d.create_session(world_seed=101)
        building = session.world.active_chunks[(0, 0)].buildings[0]
        for segment in building.all_segments()[:3]:
            game_3d.demolish_segment(session, building, segment)
        for _ in range(30):
            game_3d.update_gameplay(session, game_3d.Vector3())
        self.assertTrue(session.running)
        self.assertFalse(getattr(session, "game_over", False))
        self.assertFalse(getattr(session, "game_won", False))

    def test_new_session_bootstrap_resets_seed_count_and_camera_state(self) -> None:
        old_session = game_3d.create_session(world_seed=111)
        building = old_session.world.active_chunks[(0, 0)].buildings[0]
        game_3d.demolish_segment(
            old_session,
            building,
            building.segment((building.building_id, 0, 0, "column")),
        )
        self.assertGreater(old_session.destroyed_count, 0)

        new_session = game_3d.create_session(world_seed=222)
        self.assertEqual(new_session.world_seed, 222)
        self.assertEqual(new_session.frame, 0)
        self.assertEqual(new_session.destroyed_count, 0)
        self.assertEqual(new_session.counted_segment_keys, set())
        self.assertEqual(new_session.respawn_overrides, {})
        self.assertEqual(new_session.player.position, game_3d.Vector3(0, game_3d.PLAYER_HALF_HEIGHT, 0))
        self.assertEqual(new_session.camera.yaw, 0.0)
        self.assertFalse(new_session.camera.orbiting)

    def test_escape_quit_and_input_release_clean_up_session_controls(self) -> None:
        session = game_3d.create_session(world_seed=333)
        game_3d.handle_game_event(
            session,
            pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_w}),
        )
        game_3d.handle_game_event(
            session,
            pygame.event.Event(pygame.MOUSEBUTTONDOWN, {"button": 3, "pos": (0, 0)}),
        )
        self.assertIn(pygame.K_w, session.held_keys)
        self.assertTrue(session.camera.orbiting)
        game_3d.handle_game_event(
            session,
            pygame.event.Event(pygame.KEYUP, {"key": pygame.K_w}),
        )
        self.assertNotIn(pygame.K_w, session.held_keys)
        game_3d.handle_game_event(
            session,
            pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_ESCAPE}),
        )
        self.assertFalse(session.running)
        self.assertFalse(session.camera.orbiting)
        self.assertEqual(session.held_keys, set())

        quit_session = game_3d.create_session(world_seed=334)
        game_3d.handle_game_event(
            quit_session,
            pygame.event.Event(pygame.MOUSEBUTTONDOWN, {"button": 3, "pos": (0, 0)}),
        )
        game_3d.handle_game_event(
            quit_session,
            pygame.event.Event(pygame.QUIT, {}),
        )
        self.assertFalse(quit_session.running)
        self.assertFalse(quit_session.camera.orbiting)

    def test_representative_exploration_keeps_streaming_and_session_bounded(self) -> None:
        session = game_3d.create_session(world_seed=335)
        for _ in range(900):
            game_3d.update_gameplay(session, game_3d.Vector3(1, 0, 0))
            self.assertLessEqual(session.world.loaded_chunk_count, game_3d.MAX_LOADED_CHUNKS)
            self.assertLessEqual(len(session.debris), game_3d.MAX_DEBRIS)
            self.assertLessEqual(len(session.effects), game_3d.MAX_EFFECTS)
        self.assertTrue(session.running)
        self.assertGreaterEqual(len(session.world.active_chunks), 1)


class FeatureFoundationTests(PygameTestCase):
    def test_stable_keys_visibility_boundary_and_new_session_defaults(self) -> None:
        session = self.make_session()
        building = session.world.active_chunks[(0, 0)].buildings[0]
        segment = building.all_segments()[0]
        self.assertEqual(game_3d.stable_segment_key(segment), segment.segment_id)
        self.assertEqual(game_3d.segment_key(segment), segment.segment_id)
        self.assertEqual(len(session.world.active_chunks), 9)
        self.assertEqual(len(session.world.visible_chunks), game_3d.MAX_VISIBLE_CHUNKS)
        self.assertTrue(
            set(session.world.active_chunks).issubset(session.world.visible_chunks)
        )
        self.assertTrue(
            set(session.world.visible_chunks).difference(session.world.active_chunks)
        )
        self.assertTrue(session.player.has_gun)
        self.assertFalse(session.player.gun_equipped)
        self.assertEqual(session.player.fire_cooldown_frames, 0)
        self.assertEqual(session.damage_overrides, {})
        self.assertEqual(session.bullets, [])
        self.assertIsNone(session.pull_action)

    def test_collision_query_is_local_but_keeps_nearby_buildings(self) -> None:
        session = self.make_session(9002)
        near = self.make_segment_building("near:0:0:0", game_3d.Vector3(0, 0, 4))
        far = self.make_segment_building("far:0:0:0", game_3d.Vector3(100, 0, 0))
        session.world.active_chunks.clear()
        session.world.active_chunks[(0, 0)] = game_3d.CityChunk((0, 0), 1, [near, far])

        entries = game_3d.nearby_static_collision_entries(session)
        entry_ids = {segment.segment_id for _, segment, _ in entries}
        self.assertIn(near.all_segments()[0].segment_id, entry_ids)
        self.assertNotIn(far.all_segments()[0].segment_id, entry_ids)

    def test_transient_reset_does_not_clear_intact_segment_damage(self) -> None:
        session = self.make_session()
        building = self.make_segment_building("foundation:0:0:0")
        self.install_building(session, building)
        segment = building.segment((building.building_id, 0, 0, "column"))
        self.assertIsNotNone(segment)
        game_3d.apply_bullet_hit(session, building, segment)
        session.held_mouse_buttons.add(1)
        session.pull_action = game_3d.PullAction(
            segment.segment_id, (1, 1), (40, 1)
        )
        session.add_bullet(game_3d.Bullet(game_3d.Vector3(), game_3d.Vector3(1, 0, 0)))
        session.player.fire_cooldown_frames = 4
        game_3d.respawn_player(session)
        self.assertEqual(session.damage_overrides[segment.segment_id], 1)
        self.assertEqual(segment.bullet_hits, 1)
        self.assertEqual(session.bullets, [])
        self.assertIsNone(session.pull_action)
        self.assertEqual(session.held_mouse_buttons, set())
        self.assertEqual(session.player.fire_cooldown_frames, 0)

    def test_focus_loss_and_escape_clear_all_transient_controls(self) -> None:
        session = self.make_session()
        session.held_mouse_buttons.update({1, 3})
        session.pull_action = game_3d.PullAction(("missing",), (0, 0), (30, 0))
        session.player.fire_cooldown_frames = 5
        game_3d.handle_game_event(
            session,
            pygame.event.Event(pygame.WINDOWFOCUSLOST, {}),
        )
        self.assertEqual(session.held_mouse_buttons, set())
        self.assertIsNone(session.pull_action)
        self.assertFalse(session.camera.orbiting)
        self.assertEqual(session.player.fire_cooldown_frames, 0)
        session.held_mouse_buttons.add(1)
        game_3d.handle_game_event(
            session,
            pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_ESCAPE}),
        )
        self.assertFalse(session.running)
        self.assertEqual(session.held_mouse_buttons, set())

    def test_bounded_transient_collections_and_non_negative_timers(self) -> None:
        session = self.make_session()
        for _ in range(game_3d.MAX_BULLETS + 12):
            session.add_bullet(
                game_3d.Bullet(
                    game_3d.Vector3(),
                    game_3d.Vector3(1, 0, 0),
                    remaining_frames=1,
                )
            )
        self.assertLessEqual(len(session.bullets), game_3d.MAX_BULLETS)
        session.player.fire_cooldown_frames = 100
        for _ in range(120):
            session.advance_frame()
        self.assertEqual(session.player.fire_cooldown_frames, 0)
        self.assertTrue(all(bullet.remaining_frames >= 0 for bullet in session.bullets))


class PullInteractionTests(PygameTestCase):
    def prepare_target(self, seed: int = 9100) -> tuple[game_3d.SessionState, game_3d.Building, game_3d.BuildingSegment, tuple[int, int]]:
        session = self.make_session(seed)
        building = self.make_segment_building(f"pull:{seed}:0:0")
        self.install_building(session, building)
        segment = building.segment((building.building_id, 0, 0, "column"))
        self.assertIsNotNone(segment)
        return session, building, segment, self.segment_cursor(session, building, segment)

    def send_pull(self, session: game_3d.SessionState, cursor: tuple[int, int], drag: int = 30) -> None:
        game_3d.handle_game_event(
            session,
            pygame.event.Event(pygame.MOUSEBUTTONDOWN, {"button": 1, "pos": cursor}),
            (800, 600),
        )
        game_3d.handle_game_event(
            session,
            pygame.event.Event(
                pygame.MOUSEMOTION,
                {"pos": (cursor[0] + drag, cursor[1]), "rel": (drag, 0)},
            ),
            (800, 600),
        )
        game_3d.handle_game_event(
            session,
            pygame.event.Event(
                pygame.MOUSEBUTTONUP,
                {"button": 1, "pos": (cursor[0] + drag, cursor[1])},
            ),
            (800, 600),
        )

    def test_ten_standing_jump_and_land_scenarios_never_demolish(self) -> None:
        for index in range(10):
            session = self.make_session(9200 + index)
            building = self.make_segment_building(f"stand:{index}:0:0")
            self.install_building(session, building)
            segment = building.segment((building.building_id, 0, -1, "slab"))
            self.assertIsNotNone(segment)
            session.player.position = game_3d.Vector3(
                building.origin.x,
                game_3d.FLOOR_HEIGHT + game_3d.PLAYER_HALF_HEIGHT,
                building.origin.z,
            )
            session.player.last_safe_position = game_3d.Vector3(session.player.position)
            for _ in range(5):
                game_3d.update_gameplay(session, game_3d.Vector3())
            game_3d.update_gameplay(session, game_3d.Vector3(), jump_requested=True)
            for _ in range(60):
                game_3d.update_gameplay(session, game_3d.Vector3())
            self.assertEqual(session.destroyed_count, 0)
            self.assertEqual(segment.status, game_3d.INTACT)
            self.assertTrue(session.player.grounded)

    def test_ten_pull_cases_cover_cancel_invalid_suppression_and_exact_completion(self) -> None:
        cases = []
        valid, building, segment, cursor = self.prepare_target(9300)
        self.send_pull(valid, cursor)
        self.assertIsNotNone(valid.pull_action)
        for _ in range(game_3d.PULL_ANIMATION_FRAMES):
            game_3d.update_gameplay(valid, game_3d.Vector3())
        cases.append(valid.destroyed_count >= 1 and segment.status == game_3d.FALLING)

        short, _, short_segment, short_cursor = self.prepare_target(9301)
        self.send_pull(short, short_cursor, drag=0)
        cases.append(short.pull_action is None and short_segment.status == game_3d.INTACT)

        below, _, below_segment, below_cursor = self.prepare_target(9302)
        self.send_pull(below, below_cursor, drag=game_3d.PULL_TRIGGER_PIXELS - 1)
        cases.append(below.pull_action is None and below_segment.status == game_3d.INTACT)

        empty = self.make_session(9303)
        for chunk in empty.world.active_chunks.values():
            chunk.buildings = []
        game_3d.handle_game_event(
            empty,
            pygame.event.Event(pygame.MOUSEBUTTONDOWN, {"button": 1, "pos": (5, 5)}),
            (800, 600),
        )
        cases.append(empty.pull_action is None)

        far, far_building, far_segment, far_cursor = self.prepare_target(9304)
        far_building.origin = game_3d.Vector3(0, 0, 100)
        self.send_pull(far, far_cursor)
        cases.append(far.pull_action is None and far_segment.status == game_3d.INTACT)

        distant = self.make_session(9305)
        outer_coord = next(
            coord
            for coord in distant.world.visible_chunks
            if coord not in distant.world.active_chunks and coord[0] == 0 and coord[1] == 2
        )
        outer_building = distant.world.visible_chunks[outer_coord].buildings[0]
        outer_segment = outer_building.all_segments()[0]
        outer_cursor = self.segment_cursor(distant, outer_building, outer_segment)
        for chunk in distant.world.active_chunks.values():
            chunk.buildings = []
        game_3d.handle_game_event(
            distant,
            pygame.event.Event(pygame.MOUSEBUTTONDOWN, {"button": 1, "pos": outer_cursor}),
            (800, 600),
        )
        cases.append(distant.pull_action is None)

        orbit, _, orbit_segment, orbit_cursor = self.prepare_target(9306)
        game_3d.handle_game_event(
            orbit,
            pygame.event.Event(pygame.MOUSEBUTTONDOWN, {"button": 3, "pos": (0, 0)}),
            (800, 600),
        )
        self.send_pull(orbit, orbit_cursor)
        cases.append(orbit.pull_action is None and orbit_segment.status == game_3d.INTACT)

        focus, _, focus_segment, focus_cursor = self.prepare_target(9307)
        game_3d.handle_game_event(
            focus,
            pygame.event.Event(pygame.MOUSEBUTTONDOWN, {"button": 1, "pos": focus_cursor}),
            (800, 600),
        )
        game_3d.handle_game_event(
            focus,
            pygame.event.Event(pygame.WINDOWFOCUSLOST, {}),
            (800, 600),
        )
        cases.append(focus.pull_action is None and focus_segment.status == game_3d.INTACT)

        once, _, once_segment, once_cursor = self.prepare_target(9308)
        self.send_pull(once, once_cursor)
        for _ in range(game_3d.PULL_ANIMATION_FRAMES + 5):
            game_3d.update_gameplay(once, game_3d.Vector3())
        count_after = once.destroyed_count
        cases.append(count_after == once.destroyed_count and once_segment.status == game_3d.FALLING)

        toggle, _, toggle_segment, toggle_cursor = self.prepare_target(9309)
        game_3d.handle_game_event(
            toggle,
            pygame.event.Event(pygame.MOUSEBUTTONDOWN, {"button": 1, "pos": toggle_cursor}),
            (800, 600),
        )
        game_3d.handle_game_event(
            toggle,
            pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_1}),
            (800, 600),
        )
        cases.append(toggle.pull_action is None and toggle_segment.status == game_3d.INTACT)
        self.assertEqual(len(cases), 10)
        self.assertTrue(all(cases), cases)

    def test_pull_preview_follows_cursor_without_mutating_segment(self) -> None:
        session, building, segment, cursor = self.prepare_target(9310)
        chunk = session.world.active_chunks[(0, 0)]
        chunk.buildings = [building]
        session.world.active_chunks = {(0, 0): chunk}
        session.world.visible_chunks = {(0, 0): chunk}
        original_local_position = game_3d.Vector3(segment.local_position)
        original_aabb = segment.aabb(building.origin)

        game_3d.handle_game_event(
            session,
            pygame.event.Event(pygame.MOUSEBUTTONDOWN, {"button": 1, "pos": cursor}),
            (800, 600),
        )
        self.assertIsNotNone(session.pull_action)
        self.assertEqual(game_3d.pull_render_offset(session, segment.segment_id), game_3d.Vector3())

        moved_cursor = (cursor[0] + 48, cursor[1] - 24)
        game_3d.handle_game_event(
            session,
            pygame.event.Event(
                pygame.MOUSEMOTION,
                {"pos": moved_cursor, "rel": (48, -24)},
            ),
            (800, 600),
        )
        game_3d.update_pull(session)

        offset = game_3d.pull_render_offset(session, segment.segment_id)
        self.assertGreater(offset.length_squared(), 0.0)
        target = session.player.position + session.camera.target_offset
        before = game_3d.project_point(
            segment.world_position(building.origin), session.camera, target, (800, 600)
        )
        after = game_3d.project_point(
            segment.world_position(building.origin) + offset,
            session.camera,
            target,
            (800, 600),
        )
        self.assertIsNotNone(before)
        self.assertIsNotNone(after)
        self.assertAlmostEqual(after[0] - before[0], 48.0, delta=0.2)
        self.assertAlmostEqual(after[1] - before[1], -24.0, delta=0.2)
        game_3d.render_world(self.make_surface(), session, segment.segment_id)
        self.assertEqual(segment.local_position, original_local_position)
        self.assertEqual(segment.aabb(building.origin), original_aabb)
        self.assertEqual(segment.status, game_3d.INTACT)
        self.assertEqual(session.destroyed_count, 0)

        game_3d.handle_game_event(
            session,
            pygame.event.Event(pygame.MOUSEBUTTONUP, {"button": 1, "pos": moved_cursor}),
            (800, 600),
        )
        self.assertIsNotNone(session.pull_action)
        self.assertEqual(session.pull_action.phase, game_3d.PULL_ANIMATING)
        animation_offset = game_3d.pull_render_offset(session, segment.segment_id)
        self.assertAlmostEqual(animation_offset.x, offset.x, delta=0.001)
        self.assertAlmostEqual(animation_offset.y, offset.y, delta=0.001)
        self.assertAlmostEqual(animation_offset.z, offset.z, delta=0.001)


class WeaponAndBulletTests(PygameTestCase):
    def test_gun_toggle_modes_and_right_button_suppression(self) -> None:
        session = self.make_session(9400)
        self.assertTrue(session.player.has_gun)
        self.assertFalse(session.player.gun_equipped)
        game_3d.handle_game_event(
            session, pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_1}), (800, 600)
        )
        self.assertTrue(session.player.gun_equipped)
        game_3d.handle_game_event(
            session, pygame.event.Event(pygame.MOUSEBUTTONDOWN, {"button": 3, "pos": (0, 0)}), (800, 600)
        )
        game_3d.handle_game_event(
            session, pygame.event.Event(pygame.MOUSEBUTTONDOWN, {"button": 1, "pos": (400, 300)}), (800, 600)
        )
        self.assertEqual(session.bullets, [])
        game_3d.handle_game_event(
            session, pygame.event.Event(pygame.MOUSEBUTTONUP, {"button": 3, "pos": (0, 0)}), (800, 600)
        )
        game_3d.handle_game_event(
            session, pygame.event.Event(pygame.MOUSEBUTTONDOWN, {"button": 1, "pos": (400, 300)}), (800, 600)
        )
        self.assertEqual(len(session.bullets), 1)
        game_3d.handle_game_event(
            session, pygame.event.Event(pygame.MOUSEBUTTONUP, {"button": 1, "pos": (400, 300)}), (800, 600)
        )
        current = len(session.bullets)
        for _ in range(game_3d.FIRE_INTERVAL_FRAMES * 2):
            game_3d.update_gameplay(session, game_3d.Vector3())
        self.assertLessEqual(len(session.bullets), current)
        game_3d.handle_game_event(
            session, pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_1}), (800, 600)
        )
        self.assertFalse(session.player.gun_equipped)

    def test_fire_cadence_is_immediate_then_every_six_frames(self) -> None:
        session = self.make_session(9401)
        session.cursor_position = (10, 10)
        game_3d.handle_game_event(
            session, pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_1}), (800, 600)
        )
        with patch.object(game_3d, "fire_bullet", wraps=game_3d.fire_bullet) as fire:
            game_3d.handle_game_event(
                session,
                pygame.event.Event(pygame.MOUSEBUTTONDOWN, {"button": 1, "pos": (10, 10)}),
                (800, 600),
            )
            for _ in range(game_3d.FIRE_INTERVAL_FRAMES):
                game_3d.update_gameplay(session, game_3d.Vector3())
            self.assertEqual(fire.call_count, 2)
            for _ in range(game_3d.FIRE_INTERVAL_FRAMES):
                game_3d.update_gameplay(session, game_3d.Vector3())
            self.assertEqual(fire.call_count, 3)

    def test_bullet_lifecycle_sweep_nearest_hit_and_bounds(self) -> None:
        session = self.make_session(9402)
        session.world.active_chunks.clear()
        session.world.visible_chunks.clear()
        near = self.make_segment_building("bullet:near:0:0", game_3d.Vector3(0, 0, 4))
        far = self.make_segment_building("bullet:far:0:0", game_3d.Vector3(0, 0, 12))
        session.world.active_chunks[(0, 0)] = game_3d.CityChunk(
            (0, 0), 1, [near, far]
        )
        session.world.visible_chunks[(0, 0)] = session.world.active_chunks[(0, 0)]
        near_segment = near.segment((near.building_id, 0, 0, "column"))
        far_segment = far.segment((far.building_id, 0, 0, "column"))
        bullet = game_3d.Bullet(
            game_3d.Vector3(near_segment.world_position(near.origin).x, 1.0, 0),
            game_3d.Vector3(0, 0, 1.6),
        )
        session.bullets.append(bullet)
        game_3d.update_bullets(session)
        self.assertEqual(session.damage_overrides.get(near_segment.segment_id), 1)
        self.assertNotIn(far_segment.segment_id, session.damage_overrides)
        self.assertEqual(session.bullets, [])

        session.world.active_chunks.clear()
        session.bullets = [
            game_3d.Bullet(game_3d.Vector3(), game_3d.Vector3(1.6, 0, 0), remaining_frames=2)
        ]
        game_3d.update_bullets(session)
        game_3d.update_bullets(session)
        self.assertEqual(session.bullets, [])
        session.bullets = [game_3d.Bullet(game_3d.Vector3(), game_3d.Vector3(2, 0, 0))]
        for _ in range(31):
            game_3d.update_bullets(session)
        self.assertEqual(session.bullets, [])

    def test_bullet_cap_prunes_expired_then_evicts_oldest_active(self) -> None:
        session = self.make_session(9403)
        expired = game_3d.Bullet(game_3d.Vector3(), game_3d.Vector3(), remaining_frames=0)
        session.bullets = [expired]
        for index in range(game_3d.MAX_BULLETS):
            session.bullets.append(
                game_3d.Bullet(game_3d.Vector3(index, 0, 0), game_3d.Vector3(0, 0, 1))
            )
        new_bullet = game_3d.Bullet(game_3d.Vector3(999, 0, 0), game_3d.Vector3(0, 0, 1))
        session.add_bullet(new_bullet)
        self.assertEqual(len(session.bullets), game_3d.MAX_BULLETS)
        self.assertNotIn(expired, session.bullets)
        self.assertIn(new_bullet, session.bullets)
        self.assertEqual(session.bullets[0].position.x, 1)


class BulletDamageTests(PygameTestCase):
    def prepare_target(self, seed: int = 9500) -> tuple[game_3d.SessionState, game_3d.Building, game_3d.BuildingSegment]:
        session = self.make_session(seed)
        building = self.make_segment_building(f"damage:{seed}:0:0")
        self.install_building(session, building)
        segment = building.segment((building.building_id, 0, 0, "column"))
        self.assertIsNotNone(segment)
        return session, building, segment

    def test_hits_one_to_nine_persist_and_tenth_has_one_frame_feedback(self) -> None:
        session, building, segment = self.prepare_target()
        for hit in range(1, game_3d.BULLET_HITS_TO_BREAK):
            self.assertEqual(game_3d.apply_bullet_hit(session, building, segment), [])
            self.assertEqual(session.damage_overrides[segment.segment_id], hit)
            self.assertEqual(segment.bullet_hits, hit)
            self.assertEqual(segment.status, game_3d.INTACT)
        changed = game_3d.apply_bullet_hit(session, building, segment)
        self.assertTrue(changed)
        self.assertEqual(session.hud.target_hits, 10)
        self.assertEqual(session.hud.completion_feedback_frames, 1)
        self.assertIsNone(session.damage_overrides.get(segment.segment_id))
        self.assertEqual(segment.bullet_hits, 0)
        self.assertEqual(segment.status, game_3d.FALLING)
        game_3d.update_hud(session, (0, 0), (800, 600))
        self.assertEqual(session.hud.target_hits, 10)
        session.advance_frame()
        self.assertEqual(session.hud.completion_feedback_frames, 0)
        self.assertIsNone(session.hud.target_hits)

    def test_damage_survives_world_reload_and_clears_on_segment_lifecycle(self) -> None:
        session, building, segment = self.prepare_target(9501)
        for _ in range(3):
            game_3d.apply_bullet_hit(session, building, segment)
        session = self.make_session(9501)
        building = session.world.active_chunks[(0, 0)].buildings[0]
        segment = building.segment((building.building_id, 0, 0, "column"))
        for _ in range(3):
            game_3d.apply_bullet_hit(session, building, segment)
        session.world.ensure_active(game_3d.Vector3(game_3d.CHUNK_SIZE * 3, 0, 0), 1)
        session.world.ensure_active(game_3d.Vector3(0, 0, 0), 1)
        reloaded = session.world.find_segment(segment.segment_id)
        self.assertIsNotNone(reloaded)
        self.assertEqual(reloaded[1].bullet_hits, 3)
        self.assertEqual(session.damage_overrides[segment.segment_id], 3)
        game_3d.demolish_segment(session, building, segment, cause="pull")
        self.assertNotIn(segment.segment_id, session.damage_overrides)
        self.assertEqual(segment.bullet_hits, 0)

    def test_unique_count_and_player_respawn_rules_are_idempotent(self) -> None:
        session, building, segment = self.prepare_target(9502)
        for _ in range(game_3d.BULLET_HITS_TO_BREAK):
            game_3d.apply_bullet_hit(session, building, segment)
        count = session.destroyed_count
        for _ in range(3):
            self.assertEqual(game_3d.apply_bullet_hit(session, building, segment), [])
        self.assertEqual(session.destroyed_count, count)
        other_session, other_building, other_segment = self.prepare_target(9503)
        game_3d.apply_bullet_hit(other_session, other_building, other_segment)
        other_session.respawn_overrides[other_segment.segment_id] = game_3d.RespawnRecord(
            other_segment.segment_id, other_session.frame, (0, 0), other_session.frame
        )
        game_3d.demolish_segment(other_session, other_building, other_segment, cause="pull")
        other_session.frame = other_segment.respawn_frame or game_3d.RESPAWN_FRAMES
        game_3d.update_respawns_for_building(other_session, other_building)
        self.assertEqual(other_segment.bullet_hits, 0)


class VisibilityAndRenderTests(PygameTestCase):
    def test_visible_horizon_is_bounded_and_outer_ring_is_non_interactive(self) -> None:
        session = self.make_session(9600)
        world = session.world
        self.assertEqual(len(world.visible_target_coords((0, 0))), 25)
        self.assertLessEqual(len(world.visible_chunks), game_3d.MAX_VISIBLE_CHUNKS)
        outer = next(coord for coord in world.visible_chunks if coord not in world.active_chunks)
        outer_building = world.visible_chunks[outer].buildings[0]
        outer_segment = outer_building.all_segments()[0]
        active_ids = {segment.segment_id for _, segment in world.static_segments()}
        self.assertNotIn(outer_segment.segment_id, active_ids)
        self.assertIsNone(
            game_3d.nearest_bullet_target(
                session,
                outer_segment.world_position(outer_building.origin) - game_3d.Vector3(0, 0, 2),
                outer_segment.world_position(outer_building.origin) + game_3d.Vector3(0, 0, 2),
            )
        )
        world.ensure_active(game_3d.Vector3(game_3d.CHUNK_SIZE * 2.1, game_3d.PLAYER_HALF_HEIGHT, 0), 1)
        self.assertIn((2, 0), world.active_chunks)
        self.assertIn((2, 0), world.visible_chunks)
        self.assertEqual(len(world.active_chunks), 9)
        self.assertLessEqual(len(world.visible_chunks), 25)

    def test_sky_color_distances_and_bounded_render_collections(self) -> None:
        self.assertEqual(game_3d.SKY_COLOR, (170, 220, 245))
        self.assertEqual(game_3d.RENDER_DISTANCE, 180.0)
        self.assertEqual(game_3d.DETAIL_RENDER_DISTANCE, 110.0)
        session = self.make_session(9601)
        for _ in range(game_3d.MAX_BULLETS + 5):
            session.bullets.append(
                game_3d.Bullet(game_3d.Vector3(0, 1, 2), game_3d.Vector3(0, 0, 1))
            )
        session.bullets[:] = session.bullets[-game_3d.MAX_BULLETS:]
        for _ in range(game_3d.MAX_EFFECTS + 5):
            session.add_effect("PARTICLE", game_3d.Vector3())
        for _ in range(game_3d.MAX_DEBRIS + 5):
            session.add_debris(game_3d.Debris(("render",), game_3d.Vector3()))
        surface = self.make_surface()
        game_3d.render_world(surface, session)
        sky_pixels = sum(
            1
            for x in range(0, surface.get_width(), 40)
            for y in range(0, surface.get_height(), 40)
            if surface.get_at((x, y))[:3] == game_3d.SKY_COLOR
        )
        self.assertGreater(sky_pixels, 0)
        self.assertLessEqual(len(session.bullets), game_3d.MAX_BULLETS)
        self.assertLessEqual(len(session.debris), game_3d.MAX_DEBRIS)
        self.assertLessEqual(len(session.effects), game_3d.MAX_EFFECTS)


class CollapseRegressionTests(PygameTestCase):
    def test_pull_and_bullet_causes_preserve_the_existing_cascade_effects(self) -> None:
        pull_session = self.make_session(9700)
        pull_building = self.make_segment_building("collapse:pull:0:0")
        self.install_building(pull_session, pull_building)
        pull_target = pull_building.segment((pull_building.building_id, 1, 0, "column"))
        pull_changed = game_3d.demolish_segment(
            pull_session, pull_building, pull_target, cause="pull"
        )
        self.assertTrue(pull_changed)
        self.assertTrue({"FLASH", "PARTICLE", "CAMERA_SHAKE"} <= {
            effect.kind for effect in pull_session.effects
        })
        bullet_session = self.make_session(9701)
        bullet_building = self.make_segment_building("collapse:bullet:0:0")
        self.install_building(bullet_session, bullet_building)
        bullet_target = bullet_building.segment((bullet_building.building_id, 1, 1, "column"))
        for _ in range(game_3d.BULLET_HITS_TO_BREAK):
            changed = game_3d.apply_bullet_hit(bullet_session, bullet_building, bullet_target)
        self.assertTrue(changed)
        self.assertEqual(bullet_target.status, game_3d.FALLING)

    def test_cascade_starts_within_two_seconds_and_supported_columns_stay_stable(self) -> None:
        for index in range(10):
            session = self.make_session(9710 + index)
            building = self.make_segment_building(f"cascade:{index}:0:0")
            self.install_building(session, building)
            removed = building.segment((building.building_id, 1, 0, "column"))
            stable = building.segment((building.building_id, 2, 1, "column"))
            game_3d.demolish_segment(session, building, removed, cause="pull")
            self.assertEqual(removed.status, game_3d.FALLING)
            for _ in range(120):
                game_3d.update_gameplay(session, game_3d.Vector3())
            self.assertEqual(stable.status, game_3d.INTACT)
            self.assertLessEqual(session.destroyed_count, len(session.counted_segment_keys))

    def test_respawn_clears_segment_damage_but_not_unique_count(self) -> None:
        session = self.make_session(9720)
        building = self.make_segment_building("respawn:feature:0:0")
        self.install_building(session, building)
        segment = building.segment((building.building_id, 0, 0, "column"))
        game_3d.apply_bullet_hit(session, building, segment)
        game_3d.demolish_segment(session, building, segment, cause="bullet")
        first_count = session.destroyed_count
        session.frame = segment.respawn_frame or game_3d.RESPAWN_FRAMES
        game_3d.update_respawns_for_building(session, building)
        self.assertEqual(segment.status, game_3d.INTACT)
        self.assertEqual(segment.bullet_hits, 0)
        self.assertNotIn(segment.segment_id, session.damage_overrides)
        self.assertEqual(session.destroyed_count, first_count)
        self.assertGreaterEqual(segment.respawn_frame or 0, 0)


class HUDFeatureTests(PygameTestCase):
    def test_hud_recovers_after_pygame_font_module_restart(self) -> None:
        session = self.make_session(9799)
        surface = self.make_surface()
        game_3d.draw_hud(surface, session)
        pygame.font.quit()
        pygame.font.init()
        game_3d.draw_hud(surface, session)

    def test_hud_exposes_weapon_mode_target_progress_and_completion(self) -> None:
        session = self.make_session(9800)
        building = self.make_segment_building("hud:0:0:0")
        self.install_building(session, building)
        segment = building.segment((building.building_id, 0, 0, "column"))
        cursor = self.segment_cursor(session, building, segment)
        game_3d.update_hud(session, cursor, (800, 600))
        self.assertEqual(session.hud.weapon_state, "HOLSTERED")
        self.assertEqual(session.hud.mode_hint, "LMB drag to pull")
        self.assertEqual(session.hud.target_segment, segment.segment_id)
        self.assertEqual(session.hud.target_hits, 0)
        game_3d.handle_game_event(
            session, pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_1}), (800, 600)
        )
        game_3d.update_hud(session, cursor, (800, 600))
        self.assertEqual(session.hud.weapon_state, "EQUIPPED")
        self.assertEqual(session.hud.mode_hint, "LMB hold to fire")
        for hit in range(1, game_3d.BULLET_HITS_TO_BREAK):
            game_3d.apply_bullet_hit(session, building, segment)
            self.assertEqual(session.hud.target_hits, hit)
        game_3d.apply_bullet_hit(session, building, segment)
        surface = self.make_surface()
        game_3d.draw_hud(surface, session)
        self.assertEqual(session.hud.target_hits, game_3d.BULLET_HITS_TO_BREAK)
        self.assertEqual(session.hud.completion_feedback_frames, 1)
        session.advance_frame()
        self.assertIsNone(session.hud.target_hits)

    def test_hud_respawn_countdown_is_clamped_to_non_negative(self) -> None:
        session = self.make_session(9801)
        session.frame = 100
        segment = session.world.active_chunks[(0, 0)].buildings[0].all_segments()[0]
        session.respawn_overrides[segment.segment_id] = game_3d.RespawnRecord(
            segment.segment_id, 90, (0, 0), 0
        )
        game_3d.update_hud(session, (0, 0), (800, 600))
        self.assertIn(session.hud.respawn_remaining, (None, 0))


if __name__ == "__main__":
    unittest.main()
