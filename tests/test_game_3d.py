"""Headless tests for the NEON CITY pure gameplay seams."""

from __future__ import annotations

import os
import unittest

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

    def test_mouse_event_wires_click_demolition_and_ignores_orbit_clicks(self) -> None:
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
        click_event = pygame.event.Event(
            pygame.MOUSEBUTTONDOWN,
            {"button": 1, "pos": (projected[0], projected[1])},
        )
        game_3d.handle_game_event(session, click_event, (800, 600))
        self.assertEqual(session.destroyed_count, 0)
        game_3d.handle_game_event(
            session,
            pygame.event.Event(pygame.MOUSEBUTTONUP, {"button": 3, "pos": (0, 0)}),
            (800, 600),
        )
        game_3d.handle_game_event(session, click_event, (800, 600))
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


if __name__ == "__main__":
    unittest.main()
