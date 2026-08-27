"""NEON CITY: a small software-rendered 3D demolition sandbox.

The module is intentionally import-safe.  Pure geometry and gameplay rules are
kept outside the Pygame event loop so they can be exercised by unittest and the
headless ``--self-test`` command.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass, field
import math
import random
import sys
from typing import Iterable, Sequence

import pygame


FPS = 60
SCREEN_SIZE = (1280, 720)
FOV_DEGREES = 70.0
NEAR_PLANE = 0.1
CHUNK_SIZE = 32.0
ACTIVE_CHUNK_RADIUS = 1
MAX_LOADED_CHUNKS = 10
BUILDINGS_PER_CHUNK_MIN = 4
BUILDINGS_PER_CHUNK_MAX = 6
MIN_ACTIVE_BUILDINGS = 30
MAX_ACTIVE_BUILDINGS = 54
SPAWN_SAFE_RADIUS = 8.0
MAX_PICK_DISTANCE = 60.0
CONTACT_COOLDOWN_FRAMES = 15
DEBRIS_LIFETIME_FRAMES = 180
DEBRIS_SLOW_FRAMES = 30
MAX_EFFECT_LIFETIME_FRAMES = 45
MAX_DEBRIS = 512
MAX_EFFECTS = 256
RESPAWN_FRAMES = 1800
RECOVERY_HEIGHT = -20.0
RENDER_DISTANCE = 110.0
DETAIL_RENDER_DISTANCE = 80.0
MAX_RENDER_SEGMENTS = 120
HUD_TARGET_REFRESH_FRAMES = 4

PLAYER_SIZE = pygame.Vector3(0.8, 1.8, 0.8)
PLAYER_HALF_HEIGHT = PLAYER_SIZE.y / 2.0
PLAYER_SPEED = 0.22
PLAYER_JUMP_SPEED = 0.34
GRAVITY = 0.014
CAMERA_PITCH_MIN = -0.85
CAMERA_PITCH_MAX = 1.1
CAMERA_DISTANCE = 12.0
CAMERA_SENSITIVITY = 0.008
FLOOR_HEIGHT = 3.0
SLAB_THICKNESS = 0.24
COLUMN_THICKNESS = 0.72

Vector3 = pygame.Vector3


@dataclass(frozen=True)
class AABB:
    """Axis-aligned box represented by inclusive minimum and maximum corners."""

    minimum: Vector3
    maximum: Vector3

    @classmethod
    def from_center_size(cls, center: Vector3, size: Vector3) -> "AABB":
        half = size * 0.5
        return cls(center - half, center + half)

    @classmethod
    def from_cuboid(cls, cuboid: "Cuboid") -> "AABB":
        return cls.from_center_size(cuboid.center, cuboid.size)

    @property
    def center(self) -> Vector3:
        return (self.minimum + self.maximum) * 0.5

    @property
    def size(self) -> Vector3:
        return self.maximum - self.minimum

    def translated(self, offset: Vector3) -> "AABB":
        return AABB(self.minimum + offset, self.maximum + offset)

    def contains(self, point: Vector3) -> bool:
        return all(
            low <= value <= high
            for low, value, high in zip(self.minimum, point, self.maximum)
        )

    def intersects(self, other: "AABB") -> bool:
        return (
            self.minimum.x <= other.maximum.x
            and self.maximum.x >= other.minimum.x
            and self.minimum.y <= other.maximum.y
            and self.maximum.y >= other.minimum.y
            and self.minimum.z <= other.maximum.z
            and self.maximum.z >= other.minimum.z
        )


@dataclass(frozen=True)
class Cuboid:
    """A world-space cuboid used by the software renderer."""

    center: Vector3
    size: Vector3

    def corners(self) -> tuple[Vector3, ...]:
        half = self.size * 0.5
        x0, x1 = self.center.x - half.x, self.center.x + half.x
        y0, y1 = self.center.y - half.y, self.center.y + half.y
        z0, z1 = self.center.z - half.z, self.center.z + half.z
        return (
            Vector3(x0, y0, z0),
            Vector3(x1, y0, z0),
            Vector3(x1, y1, z0),
            Vector3(x0, y1, z0),
            Vector3(x0, y0, z1),
            Vector3(x1, y0, z1),
            Vector3(x1, y1, z1),
            Vector3(x0, y1, z1),
        )

    def aabb(self) -> AABB:
        return AABB.from_cuboid(self)


def world_to_local(point: Vector3, origin: Vector3) -> Vector3:
    """Return a point relative to an object's origin."""

    return Vector3(point.x - origin.x, point.y - origin.y, point.z - origin.z)


@dataclass
class Camera:
    """Orbit camera with a stable look-at basis for projection and picking."""

    yaw: float = 0.0
    pitch: float = 0.25
    distance: float = CAMERA_DISTANCE
    target_offset: Vector3 = field(default_factory=lambda: Vector3(0, 1, 0))
    orbiting: bool = False

    def position(self, target: Vector3) -> Vector3:
        horizontal = Vector3(math.sin(self.yaw), 0.0, math.cos(self.yaw))
        horizontal_scale = math.cos(self.pitch) * self.distance
        return Vector3(
            target.x - horizontal.x * horizontal_scale,
            target.y + math.sin(self.pitch) * self.distance,
            target.z - horizontal.z * horizontal_scale,
        )

    def forward(self, target: Vector3) -> Vector3:
        direction = target - self.position(target)
        if direction.length_squared() == 0:
            return Vector3(0, 0, 1)
        return direction.normalize()

    def basis(self, target: Vector3) -> tuple[Vector3, Vector3, Vector3, Vector3]:
        camera_position = self.position(target)
        forward = target - camera_position
        if forward.length_squared() == 0:
            forward = Vector3(0, 0, 1)
        else:
            forward = forward.normalize()
        world_up = Vector3(0, 1, 0)
        right = world_up.cross(forward)
        if right.length_squared() == 0:
            right = Vector3(1, 0, 0)
        else:
            right = right.normalize()
        up = forward.cross(right).normalize()
        return camera_position, forward, right, up

    def world_to_camera(self, point: Vector3, target: Vector3) -> Vector3:
        camera_position, forward, right, up = self.basis(target)
        relative = point - camera_position
        return Vector3(
            relative.dot(right),
            relative.dot(up),
            relative.dot(forward),
        )

    def orbit(self, delta_x: float, delta_y: float) -> None:
        self.yaw += delta_x * CAMERA_SENSITIVITY
        self.pitch = max(
            CAMERA_PITCH_MIN,
            min(CAMERA_PITCH_MAX, self.pitch + delta_y * CAMERA_SENSITIVITY),
        )


@dataclass(frozen=True)
class ProjectionContext:
    """Per-frame camera basis reused by all projected geometry."""

    camera_position: Vector3
    forward: Vector3
    right: Vector3
    up: Vector3
    focal_length: float
    screen_size: tuple[int, int]


def projection_context(
    camera: Camera,
    target: Vector3,
    screen_size: tuple[int, int],
) -> ProjectionContext:
    camera_position, forward, right, up = camera.basis(target)
    focal_length = (screen_size[0] * 0.5) / math.tan(math.radians(FOV_DEGREES) * 0.5)
    return ProjectionContext(
        camera_position=camera_position,
        forward=forward,
        right=right,
        up=up,
        focal_length=focal_length,
        screen_size=screen_size,
    )


def camera_relative_movement(camera: Camera, forward: float, strafe: float) -> Vector3:
    """Convert camera-relative forward/strafe input to a horizontal direction."""

    forward_axis = Vector3(math.sin(camera.yaw), 0.0, math.cos(camera.yaw))
    right_axis = Vector3(math.cos(camera.yaw), 0.0, -math.sin(camera.yaw))
    direction = forward_axis * float(forward) + right_axis * float(strafe)
    if direction.length_squared() > 1.0:
        direction.normalize_ip()
    return direction


@dataclass
class Player:
    """Block avatar state, including one-jump and safe-recovery invariants."""

    position: Vector3
    velocity: Vector3 = field(default_factory=Vector3)
    grounded: bool = True
    last_safe_position: Vector3 | None = None
    contact_cooldowns: dict[object, int] = field(default_factory=dict)
    slow_until_frame: int = 0
    pending_push: Vector3 = field(default_factory=Vector3)
    size: Vector3 = field(default_factory=lambda: Vector3(PLAYER_SIZE))

    def __post_init__(self) -> None:
        self.position = Vector3(self.position)
        self.velocity = Vector3(self.velocity)
        self.pending_push = Vector3(self.pending_push)
        if self.last_safe_position is None:
            self.last_safe_position = Vector3(self.position)
        else:
            self.last_safe_position = Vector3(self.last_safe_position)

    def aabb(self, position: Vector3 | None = None) -> AABB:
        return AABB.from_center_size(self.position if position is None else position, self.size)

    def try_jump(self) -> bool:
        if not self.grounded:
            return False
        self.velocity.y = PLAYER_JUMP_SPEED
        self.grounded = False
        return True


def _collisions(box: AABB, static_boxes: Iterable[AABB]) -> list[AABB]:
    return [other for other in static_boxes if box.intersects(other)]


def recover_player_if_needed(player: Player) -> bool:
    """Return the player to the last stable position below the recovery height."""

    if player.position.y >= RECOVERY_HEIGHT:
        return False
    player.position = Vector3(player.last_safe_position)
    player.velocity = Vector3()
    player.grounded = True
    return True


def update_player(
    player: Player,
    movement: Vector3,
    static_boxes: Iterable[AABB],
    frame: int,
    jump_requested: bool = False,
) -> list[AABB]:
    """Advance one fixed frame and resolve axis-separated AABB collisions."""

    boxes = list(static_boxes)
    if jump_requested:
        player.try_jump()

    direction = Vector3(movement.x, 0.0, movement.z)
    if direction.length_squared() > 1.0:
        direction.normalize_ip()
    speed_scale = 0.5 if frame < player.slow_until_frame else 1.0
    push = Vector3(player.pending_push.x, 0.0, player.pending_push.z)
    player.pending_push = Vector3()
    player.velocity.x = direction.x * PLAYER_SPEED * speed_scale + push.x
    player.velocity.z = direction.z * PLAYER_SPEED * speed_scale + push.z
    if not player.grounded:
        player.velocity.y -= GRAVITY
    else:
        player.velocity.y = min(0.0, player.velocity.y)

    contacts: list[AABB] = []
    delta_x = player.velocity.x
    candidate = player.aabb(Vector3(player.position.x + delta_x, player.position.y, player.position.z))
    hit = _collisions(candidate, boxes)
    if hit:
        contacts.extend(hit)
        player.velocity.x = 0.0
    else:
        player.position.x += delta_x

    delta_z = player.velocity.z
    candidate = player.aabb(Vector3(player.position.x, player.position.y, player.position.z + delta_z))
    hit = _collisions(candidate, boxes)
    if hit:
        contacts.extend(hit)
        player.velocity.z = 0.0
    else:
        player.position.z += delta_z

    delta_y = player.velocity.y
    candidate = player.aabb(Vector3(player.position.x, player.position.y + delta_y, player.position.z))
    hit = _collisions(candidate, boxes)
    if hit:
        contacts.extend(hit)
        if delta_y <= 0.0:
            top = max(box.maximum.y for box in hit)
            player.position.y = top + player.size.y * 0.5
            player.grounded = True
        else:
            bottom = min(box.minimum.y for box in hit)
            player.position.y = bottom - player.size.y * 0.5
            player.grounded = False
        player.velocity.y = 0.0
    elif player.position.y + delta_y - player.size.y * 0.5 <= 0.0:
        player.position.y = player.size.y * 0.5
        player.velocity.y = 0.0
        player.grounded = True
    else:
        player.position.y += delta_y
        player.grounded = False

    if player.grounded and player.position.y >= PLAYER_HALF_HEIGHT:
        player.last_safe_position = Vector3(player.position)
    recover_player_if_needed(player)
    return contacts


@dataclass(frozen=True)
class ProjectedFace:
    points: tuple[tuple[float, float], ...]
    depth: float
    face_index: int


def _project_point_with_context(
    point: Vector3,
    context: ProjectionContext,
) -> tuple[float, float, float] | None:
    relative = point - context.camera_position
    depth = relative.dot(context.forward)
    if depth <= NEAR_PLANE:
        return None
    return (
        context.screen_size[0] * 0.5
        + relative.dot(context.right) * context.focal_length / depth,
        context.screen_size[1] * 0.5
        - relative.dot(context.up) * context.focal_length / depth,
        depth,
    )


def project_point(
    point: Vector3,
    camera: Camera,
    target: Vector3,
    screen_size: tuple[int, int],
) -> tuple[float, float, float] | None:
    """Project a world point to ``(screen_x, screen_y, camera_depth)``."""

    return _project_point_with_context(point, projection_context(camera, target, screen_size))


_CUBOID_FACES: tuple[tuple[int, int, int, int], ...] = (
    (0, 1, 2, 3),
    (4, 7, 6, 5),
    (0, 4, 5, 1),
    (3, 2, 6, 7),
    (0, 3, 7, 4),
    (1, 5, 6, 2),
)
_CUBOID_FACE_NORMALS: tuple[Vector3, ...] = (
    Vector3(0, 0, -1),
    Vector3(0, 0, 1),
    Vector3(0, -1, 0),
    Vector3(0, 1, 0),
    Vector3(-1, 0, 0),
    Vector3(1, 0, 0),
)


def projected_cuboid_bounds(
    cuboid: Cuboid,
    context: ProjectionContext,
) -> tuple[float, float, float, float, float] | None:
    """Return a coarse projected rectangle and nearest depth for a cuboid.

    Picking uses this inexpensive broad-phase test before building projected
    faces and running point-in-polygon checks.  A cuboid that has at least one
    corner beyond the near plane is sufficient here because this is only a
    rejection filter; the exact face test remains authoritative.
    """

    projected_corners = [
        _project_point_with_context(corner, context) for corner in cuboid.corners()
    ]
    visible_corners = [point for point in projected_corners if point is not None]
    if not visible_corners:
        return None
    return (
        min(point[0] for point in visible_corners),
        min(point[1] for point in visible_corners),
        max(point[0] for point in visible_corners),
        max(point[1] for point in visible_corners),
        min(point[2] for point in visible_corners),
    )


def project_cuboid_faces(
    cuboid: Cuboid,
    camera: Camera,
    target: Vector3,
    screen_size: tuple[int, int],
    context: ProjectionContext | None = None,
) -> list[ProjectedFace]:
    """Project all faces fully beyond the near plane for drawing or picking."""

    context = context or projection_context(camera, target, screen_size)
    corners = cuboid.corners()
    projected_corners = [
        _project_point_with_context(corner, context) for corner in corners
    ]
    projected: list[ProjectedFace] = []
    for face_index, indices in enumerate(_CUBOID_FACES):
        if _CUBOID_FACE_NORMALS[face_index].dot(
            context.camera_position - cuboid.center
        ) <= 0.0:
            continue
        points = [projected_corners[index] for index in indices]
        if any(point is None for point in points):
            continue
        valid_points = [point for point in points if point is not None]
        projected.append(
            ProjectedFace(
                tuple((point[0], point[1]) for point in valid_points),
                sum(point[2] for point in valid_points) / len(valid_points),
                face_index,
            )
        )
    return sorted(projected, key=lambda face: face.depth, reverse=True)


def point_in_polygon(point: tuple[float, float], polygon: Sequence[tuple[float, float]]) -> bool:
    """Return whether a 2D point lies inside a polygon using ray casting."""

    x, y = point
    inside = False
    previous = polygon[-1]
    for current in polygon:
        x0, y0 = previous
        x1, y1 = current
        crosses = (y0 > y) != (y1 > y)
        if crosses and x < (x1 - x0) * (y - y0) / ((y1 - y0) or 1e-12) + x0:
            inside = not inside
        previous = current
    return inside


def shade_color(color: tuple[int, int, int], face_index: int, highlighted: bool) -> tuple[int, int, int]:
    brightness = (0.62, 0.78, 0.9, 1.05, 0.72, 0.95)[face_index]
    if highlighted:
        brightness += 0.35
    return tuple(max(0, min(255, int(channel * brightness))) for channel in color)


def draw_cuboid(
    surface: pygame.Surface,
    cuboid: Cuboid,
    camera: Camera,
    target: Vector3,
    color: tuple[int, int, int],
    highlighted: bool = False,
    context: ProjectionContext | None = None,
) -> None:
    """Draw projected cuboid faces from farthest to nearest."""

    for face in project_cuboid_faces(
        cuboid,
        camera,
        target,
        surface.get_size(),
        context=context,
    ):
        pygame.draw.polygon(
            surface,
            shade_color(color, face.face_index, highlighted),
            [(round(x), round(y)) for x, y in face.points],
        )
        if highlighted:
            pygame.draw.lines(
                surface,
                (255, 255, 255),
                True,
                [(round(x), round(y)) for x, y in face.points],
                2,
            )


@dataclass
class Effect:
    """Short-lived visual feedback that never participates in gameplay rules."""

    effect_id: int
    kind: str
    position: Vector3
    remaining_frames: int
    intensity: float = 1.0
    source_segment_id: object | None = None


BASE = "BASE"
INTACT = "INTACT"
FALLING = "FALLING"
ABSENT = "ABSENT"
PENDING_RESPAWN = "PENDING_RESPAWN"
COLUMN = "COLUMN"
SLAB = "SLAB"


@dataclass
class RespawnRecord:
    """The session-level schedule for one destroyed segment identity."""

    segment_key: tuple[object, ...]
    respawn_frame: int
    source_chunk: tuple[int, int]
    destroyed_frame: int


@dataclass
class BuildingSegment:
    """One independently selectable, destructible building cuboid."""

    segment_id: tuple[object, ...]
    building_id: str
    floor: int
    column: int
    part: str
    local_position: Vector3
    size: Vector3
    kind: str
    status: str = INTACT
    destroyed_frame: int | None = None
    respawn_frame: int | None = None
    counted: bool = False

    def world_position(self, origin: Vector3) -> Vector3:
        return origin + self.local_position

    def cuboid(self, origin: Vector3) -> Cuboid:
        return Cuboid(self.world_position(origin), self.size)

    def aabb(self, origin: Vector3) -> AABB:
        return self.cuboid(origin).aabb()


@dataclass
class Building:
    """A deterministic building made from four column chains and slabs."""

    building_id: str
    origin: Vector3
    width: float
    depth: float
    floor_count: int
    color: tuple[int, int, int]
    segments: dict[tuple[object, ...], BuildingSegment] = field(default_factory=dict)
    support_edges: dict[tuple[object, ...], set[object]] = field(default_factory=dict)

    @classmethod
    def create(
        cls,
        building_id: str,
        origin: Vector3,
        width: float,
        depth: float,
        floor_count: int,
        color: tuple[int, int, int],
    ) -> "Building":
        building = cls(
            building_id=building_id,
            origin=Vector3(origin),
            width=float(width),
            depth=float(depth),
            floor_count=int(floor_count),
            color=color,
        )
        x_offset = width * 0.5 - COLUMN_THICKNESS * 0.5
        z_offset = depth * 0.5 - COLUMN_THICKNESS * 0.5
        columns = (
            (-x_offset, -z_offset),
            (x_offset, -z_offset),
            (-x_offset, z_offset),
            (x_offset, z_offset),
        )
        for floor in range(floor_count):
            for column, (x, z) in enumerate(columns):
                segment_id = (building_id, floor, column, "column")
                segment = BuildingSegment(
                    segment_id=segment_id,
                    building_id=building_id,
                    floor=floor,
                    column=column,
                    part="column",
                    local_position=Vector3(
                        x,
                        floor * FLOOR_HEIGHT + FLOOR_HEIGHT * 0.5,
                        z,
                    ),
                    size=Vector3(COLUMN_THICKNESS, FLOOR_HEIGHT, COLUMN_THICKNESS),
                    kind=COLUMN,
                )
                building.segments[segment_id] = segment
                if floor == 0:
                    building.support_edges[segment_id] = {BASE}
                else:
                    building.support_edges[segment_id] = {
                        (building_id, floor - 1, column, "column")
                    }

            slab_id = (building_id, floor, -1, "slab")
            slab = BuildingSegment(
                segment_id=slab_id,
                building_id=building_id,
                floor=floor,
                column=-1,
                part="slab",
                local_position=Vector3(
                    0,
                    (floor + 1) * FLOOR_HEIGHT - SLAB_THICKNESS * 0.5,
                    0,
                ),
                size=Vector3(width, SLAB_THICKNESS, depth),
                kind=SLAB,
            )
            building.segments[slab_id] = slab
            building.support_edges[slab_id] = {
                (building_id, floor, column, "column") for column in range(4)
            }
        return building

    def all_segments(self) -> list[BuildingSegment]:
        return list(self.segments.values())

    def segment(self, segment_id: tuple[object, ...]) -> BuildingSegment | None:
        return self.segments.get(segment_id)

    def distance_to_xz(self, point: Vector3) -> float:
        return math.hypot(self.origin.x - point.x, self.origin.z - point.z)

    def footprint_intersects(self, other: "Building") -> bool:
        left = self.origin.x - self.width * 0.5
        right = self.origin.x + self.width * 0.5
        front = self.origin.z - self.depth * 0.5
        back = self.origin.z + self.depth * 0.5
        other_left = other.origin.x - other.width * 0.5
        other_right = other.origin.x + other.width * 0.5
        other_front = other.origin.z - other.depth * 0.5
        other_back = other.origin.z + other.depth * 0.5
        return left < other_right and right > other_left and front < other_back and back > other_front

    def supported_segment_ids(self) -> set[object]:
        """Return intact segments that have an intact path to the base."""

        supported: set[object] = {BASE}
        changed = True
        while changed:
            changed = False
            for segment_id, segment in self.segments.items():
                if segment.status != INTACT or segment_id in supported:
                    continue
                if any(edge in supported for edge in self.support_edges.get(segment_id, set())):
                    supported.add(segment_id)
                    changed = True
        return supported

    def can_restore(self, segment: BuildingSegment) -> bool:
        """Check direct support after lower floors have been restored."""

        return any(
            edge == BASE
            or (
                isinstance(edge, tuple)
                and self.segments.get(edge) is not None
                and self.segments[edge].status == INTACT
            )
            for edge in self.support_edges.get(segment.segment_id, set())
        )


def stable_chunk_seed(world_seed: int, coord: tuple[int, int]) -> int:
    """Mix a session seed and chunk coordinate without using process-randomized hash()."""

    x, z = coord
    value = (int(world_seed) ^ (x * 73856093) ^ (z * 19349663)) & 0xFFFFFFFF
    value = (value * 1664525 + 1013904223) & 0xFFFFFFFF
    return value


@dataclass
class CityChunk:
    coord: tuple[int, int]
    seed: int
    buildings: list[Building]
    loaded_frame: int = 0

    @classmethod
    def generate(
        cls,
        world_seed: int,
        coord: tuple[int, int],
        safe_center: Vector3 | None = None,
        loaded_frame: int = 0,
    ) -> "CityChunk":
        seed = stable_chunk_seed(world_seed, coord)
        rng = random.Random(seed)
        safe_center = Vector3() if safe_center is None else Vector3(safe_center)
        local_lots = [
            (5.0, 5.0),
            (16.0, 5.0),
            (27.0, 5.0),
            (5.0, 16.0),
            (16.0, 16.0),
            (27.0, 16.0),
            (5.0, 27.0),
            (16.0, 27.0),
            (27.0, 27.0),
        ]
        rng.shuffle(local_lots)
        target_count = rng.randint(BUILDINGS_PER_CHUNK_MIN, BUILDINGS_PER_CHUNK_MAX)
        buildings: list[Building] = []
        base_x = coord[0] * CHUNK_SIZE
        base_z = coord[1] * CHUNK_SIZE

        for lot_index, (local_x, local_z) in enumerate(local_lots):
            width = rng.uniform(5.5, 8.0)
            depth = rng.uniform(5.5, 8.0)
            origin = Vector3(base_x + local_x, 0.0, base_z + local_z)
            if math.hypot(origin.x - safe_center.x, origin.z - safe_center.z) < (
                SPAWN_SAFE_RADIUS + max(width, depth) * 0.5
            ):
                continue
            candidate = Building.create(
                building_id=f"b:{coord[0]}:{coord[1]}:{lot_index}",
                origin=origin,
                width=width,
                depth=depth,
                floor_count=rng.randint(4, 8),
                color=rng.choice(
                    (
                        (36, 190, 220),
                        (176, 74, 220),
                        (255, 94, 176),
                        (62, 224, 154),
                        (255, 176, 70),
                    )
                ),
            )
            if any(candidate.footprint_intersects(existing) for existing in buildings):
                continue
            buildings.append(candidate)
            if len(buildings) >= target_count:
                break

        # The 3x3 world must remain dense even if a seed rejects several lots.
        fallback_index = len(local_lots)
        while len(buildings) < BUILDINGS_PER_CHUNK_MIN:
            grid_x = 4.0 + ((fallback_index * 7) % 24)
            grid_z = 4.0 + ((fallback_index * 11) % 24)
            fallback_index += 1
            width = 5.5
            depth = 5.5
            origin = Vector3(base_x + grid_x, 0.0, base_z + grid_z)
            candidate = Building.create(
                building_id=f"b:{coord[0]}:{coord[1]}:fallback:{fallback_index}",
                origin=origin,
                width=width,
                depth=depth,
                floor_count=4 + fallback_index % 5,
                color=(60, 180, 240),
            )
            if math.hypot(origin.x - safe_center.x, origin.z - safe_center.z) < SPAWN_SAFE_RADIUS + 3:
                continue
            if any(candidate.footprint_intersects(existing) for existing in buildings):
                continue
            buildings.append(candidate)

        buildings.sort(key=lambda building: building.building_id)
        return cls(coord=coord, seed=seed, buildings=buildings, loaded_frame=loaded_frame)


class CityWorld:
    """Deterministic bounded 3x3 chunk streaming and segment lookup boundary."""

    def __init__(
        self,
        world_seed: int,
        session: "SessionState | None" = None,
        respawn_overrides: dict[tuple[object, ...], RespawnRecord] | None = None,
        counted_segment_keys: set[tuple[object, ...]] | None = None,
    ) -> None:
        self.world_seed = int(world_seed)
        self.session = session
        self.active_chunks: dict[tuple[int, int], CityChunk] = {}
        self.pending_chunk: CityChunk | None = None
        self.frame = 0
        self.respawn_overrides = respawn_overrides if respawn_overrides is not None else {}
        self.counted_segment_keys = (
            counted_segment_keys if counted_segment_keys is not None else set()
        )

    @property
    def loaded_chunk_count(self) -> int:
        return len(self.active_chunks) + (1 if self.pending_chunk is not None else 0)

    @staticmethod
    def chunk_coord(position: Vector3) -> tuple[int, int]:
        return math.floor(position.x / CHUNK_SIZE), math.floor(position.z / CHUNK_SIZE)

    @staticmethod
    def target_coords(center: tuple[int, int]) -> list[tuple[int, int]]:
        cx, cz = center
        return [
            (cx + dx, cz + dz)
            for dz in range(-ACTIVE_CHUNK_RADIUS, ACTIVE_CHUNK_RADIUS + 1)
            for dx in range(-ACTIVE_CHUNK_RADIUS, ACTIVE_CHUNK_RADIUS + 1)
        ]

    def _apply_overrides(self, chunk: CityChunk) -> None:
        for building in chunk.buildings:
            for segment in building.all_segments():
                segment.counted = segment.segment_id in self.counted_segment_keys
                record = self.respawn_overrides.get(segment.segment_id)
                if record is None:
                    continue
                segment.destroyed_frame = record.destroyed_frame
                segment.respawn_frame = record.respawn_frame
                segment.status = (
                    ABSENT if self.frame < record.respawn_frame else PENDING_RESPAWN
                )
            self._restore_ready_segments(building)

    def _restore_ready_segments(self, building: Building) -> None:
        for segment in sorted(building.all_segments(), key=_respawn_sort_key):
            record = self.respawn_overrides.get(segment.segment_id)
            if record is None or self.frame < record.respawn_frame:
                continue
            if segment.status in (ABSENT, PENDING_RESPAWN) and building.can_restore(segment):
                segment.status = INTACT
                segment.destroyed_frame = None
                segment.respawn_frame = None
                self.respawn_overrides.pop(segment.segment_id, None)

    def _generate_chunk(self, coord: tuple[int, int]) -> CityChunk:
        chunk = CityChunk.generate(
            self.world_seed,
            coord,
            safe_center=Vector3(0, 0, 0),
            loaded_frame=self.frame,
        )
        self._apply_overrides(chunk)
        return chunk

    def ensure_active(self, player_position: Vector3, frame: int = 0) -> None:
        """Keep exactly nine current chunks, with at most one incoming swap buffer."""

        self.frame = int(frame)
        center = self.chunk_coord(player_position)
        target = set(self.target_coords(center))
        missing = sorted(target.difference(self.active_chunks))
        for coord in missing:
            self.pending_chunk = self._generate_chunk(coord)
            self.active_chunks[coord] = self.pending_chunk
            self.pending_chunk = None
            if len(self.active_chunks) > MAX_LOADED_CHUNKS:
                removable = sorted(set(self.active_chunks).difference(target))
                if removable:
                    self.active_chunks.pop(removable[0], None)
        for coord in list(self.active_chunks):
            if coord not in target:
                self.active_chunks.pop(coord, None)
        self._enforce_density()

    def _enforce_density(self) -> None:
        total = len(self.all_buildings())
        if total >= MIN_ACTIVE_BUILDINGS:
            return
        for chunk in self.active_chunks.values():
            if total >= MIN_ACTIVE_BUILDINGS:
                break
            # Normal generation already supplies four buildings per chunk; this
            # branch is a deterministic safety net for future generator changes.
            while len(chunk.buildings) < BUILDINGS_PER_CHUNK_MAX and total < MIN_ACTIVE_BUILDINGS:
                index = len(chunk.buildings)
                origin = Vector3(
                    chunk.coord[0] * CHUNK_SIZE + 4 + index * 5,
                    0,
                    chunk.coord[1] * CHUNK_SIZE + 28,
                )
                candidate = Building.create(
                    building_id=f"b:{chunk.coord[0]}:{chunk.coord[1]}:density:{index}",
                    origin=origin,
                    width=5.0,
                    depth=5.0,
                    floor_count=4 + index % 4,
                    color=(48, 160, 220),
                )
                if any(candidate.footprint_intersects(other) for other in chunk.buildings):
                    break
                chunk.buildings.append(candidate)
                total += 1
            chunk.buildings.sort(key=lambda building: building.building_id)

    def all_buildings(self) -> list[Building]:
        return [
            building
            for coord in sorted(self.active_chunks)
            for building in self.active_chunks[coord].buildings
        ]

    def all_segments(self) -> list[BuildingSegment]:
        return [segment for building in self.all_buildings() for segment in building.all_segments()]

    def static_segments(self) -> list[tuple[Building, BuildingSegment]]:
        return [
            (building, segment)
            for building in self.all_buildings()
            for segment in building.all_segments()
            if segment.status == INTACT
        ]

    def static_aabbs(self) -> list[AABB]:
        return [segment.aabb(building.origin) for building, segment in self.static_segments()]

    def chunk_layout(self, coord: tuple[int, int]) -> tuple[tuple[object, ...], ...]:
        chunk = self.active_chunks[coord]
        return tuple(
            (
                building.building_id,
                tuple(round(value, 4) for value in building.origin),
                round(building.width, 4),
                round(building.depth, 4),
                building.floor_count,
            )
            for building in chunk.buildings
        )

    def find_segment(
        self, segment_id: tuple[object, ...]
    ) -> tuple[Building, BuildingSegment] | None:
        for building in self.all_buildings():
            segment = building.segment(segment_id)
            if segment is not None:
                return building, segment
        return None


def _respawn_sort_key(segment: BuildingSegment) -> tuple[int, int, int]:
    """Restore same-floor columns before their slab can depend on them."""

    return segment.floor, int(segment.part == "slab"), segment.column


@dataclass
class Debris:
    """A short-lived falling piece that can push or slow the player."""

    source_segment_id: tuple[object, ...]
    position: Vector3
    velocity: Vector3 = field(default_factory=lambda: Vector3(0, -0.02, 0))
    remaining_frames: int = DEBRIS_LIFETIME_FRAMES
    push_radius: float = 1.6
    size: Vector3 = field(default_factory=lambda: Vector3(0.7, 0.7, 0.7))

    def __post_init__(self) -> None:
        self.position = Vector3(self.position)
        self.velocity = Vector3(self.velocity)
        self.remaining_frames = max(0, min(DEBRIS_LIFETIME_FRAMES, self.remaining_frames))

    def cuboid(self) -> Cuboid:
        return Cuboid(self.position, self.size)

    def update(self) -> None:
        self.velocity.y -= GRAVITY * 0.55
        self.position += self.velocity
        self.remaining_frames = max(0, self.remaining_frames - 1)


@dataclass
class HUDState:
    """Player-facing summary derived from the current session state."""

    target_segment: tuple[object, ...] | None = None
    destroyed_count: int = 0
    respawn_remaining: int | None = None
    control_hint: str = "WASD Move  Space Jump  RMB Orbit  LMB Demolish  Esc Quit"


class SessionState:
    """Launch-to-exit state shared by the headless seams and interactive loop."""

    def __init__(self, world_seed: int | None = None) -> None:
        self.world_seed = int(random.randrange(1, 2**31) if world_seed is None else world_seed)
        self.frame = 0
        self.player = Player(Vector3(0, PLAYER_HALF_HEIGHT, 0))
        self.camera = Camera()
        self.respawn_overrides: dict[tuple[object, ...], RespawnRecord] = {}
        self.counted_segment_keys: set[tuple[object, ...]] = set()
        self.destroyed_count = 0
        self.debris: list[Debris] = []
        self.effects: list[Effect] = []
        self.hud = HUDState()
        self.running = True
        self.held_keys: set[int] = set()
        self.world = CityWorld(
            self.world_seed,
            session=self,
            respawn_overrides=self.respawn_overrides,
            counted_segment_keys=self.counted_segment_keys,
        )
        self.world.ensure_active(self.player.position, self.frame)
        self.active_chunks = self.world.active_chunks

    def add_effect(
        self,
        kind: str,
        position: Vector3,
        lifetime: int = MAX_EFFECT_LIFETIME_FRAMES,
        intensity: float = 1.0,
        source_segment_id: object | None = None,
    ) -> Effect:
        lifetime = max(1, min(MAX_EFFECT_LIFETIME_FRAMES, int(lifetime)))
        effect = Effect(
            effect_id=self.frame + len(self.effects),
            kind=kind,
            position=Vector3(position),
            remaining_frames=lifetime,
            intensity=max(0.0, float(intensity)),
            source_segment_id=source_segment_id,
        )
        self.effects.append(effect)
        if len(self.effects) > MAX_EFFECTS:
            self.effects.pop(0)
        return effect

    def advance_frame(self) -> None:
        """Advance fixed-frame timers and remove expired effects."""

        self.frame += 1
        self.world.frame = self.frame
        for effect in self.effects:
            effect.remaining_frames = max(0, effect.remaining_frames - 1)
        self.effects[:] = [effect for effect in self.effects if effect.remaining_frames > 0]

    def register_segment_count(self, segment: BuildingSegment) -> bool:
        """Count a stable segment identity once for this session."""

        if segment.segment_id in self.counted_segment_keys:
            segment.counted = True
            return False
        self.counted_segment_keys.add(segment.segment_id)
        segment.counted = True
        self.destroyed_count += 1
        return True

    def add_debris(self, debris: Debris) -> None:
        self.debris.append(debris)
        if len(self.debris) > MAX_DEBRIS:
            self.debris.pop(0)

    def clear_input_state(self) -> None:
        """Release transient controls when the window closes or loses focus."""

        self.held_keys.clear()
        self.camera.orbiting = False


def create_session(world_seed: int | None = None) -> SessionState:
    """Bootstrap a fresh, in-memory sandbox session with reset statistics."""

    return SessionState(world_seed=world_seed)


def contact_is_ready(player: Player, segment_key: object, frame: int) -> bool:
    """Apply the fixed cooldown that prevents repeated continuous contacts."""

    last_frame = player.contact_cooldowns.get(segment_key)
    if last_frame is not None and frame - last_frame < CONTACT_COOLDOWN_FRAMES:
        return False
    player.contact_cooldowns[segment_key] = frame
    return True


def _source_chunk_for_building(building: Building) -> tuple[int, int]:
    parts = building.building_id.split(":")
    try:
        return int(parts[1]), int(parts[2])
    except (IndexError, ValueError):
        return 0, 0


def _mark_segment_falling(
    session: SessionState,
    building: Building,
    segment: BuildingSegment,
) -> bool:
    if segment.status != INTACT:
        return False
    segment.status = FALLING
    segment.destroyed_frame = session.frame
    segment.respawn_frame = session.frame + RESPAWN_FRAMES
    session.respawn_overrides[segment.segment_id] = RespawnRecord(
        segment_key=segment.segment_id,
        respawn_frame=segment.respawn_frame,
        source_chunk=_source_chunk_for_building(building),
        destroyed_frame=session.frame,
    )
    session.register_segment_count(segment)
    session.add_debris(
        Debris(
            source_segment_id=segment.segment_id,
            position=segment.world_position(building.origin),
            velocity=Vector3(0.0, 0.04, 0.0),
        )
    )
    session.add_effect(
        "FLASH",
        segment.world_position(building.origin),
        lifetime=12,
        intensity=1.0,
        source_segment_id=segment.segment_id,
    )
    session.add_effect(
        "PARTICLE",
        segment.world_position(building.origin),
        lifetime=24,
        intensity=0.9,
        source_segment_id=segment.segment_id,
    )
    session.add_effect(
        "CAMERA_SHAKE",
        segment.world_position(building.origin),
        lifetime=10,
        intensity=0.35,
        source_segment_id=segment.segment_id,
    )
    return True


def evaluate_support_cascade(
    session: SessionState,
    building: Building,
) -> list[BuildingSegment]:
    """Move every newly unreachable intact segment into FALLING in one frame."""

    supported = building.supported_segment_ids()
    changed: list[BuildingSegment] = []
    for segment in sorted(building.all_segments(), key=lambda item: (item.floor, item.column)):
        if segment.status == INTACT and segment.segment_id not in supported:
            if _mark_segment_falling(session, building, segment):
                changed.append(segment)
    return changed


def apply_debris_contact(player: Player, debris: Debris, frame: int) -> bool:
    """Push the player away and apply a bounded slowdown when debris is close."""

    offset = Vector3(player.position.x - debris.position.x, 0.0, player.position.z - debris.position.z)
    distance = offset.length()
    if distance > debris.push_radius:
        return False
    direction = offset.normalize() if distance > 1e-6 else Vector3(0, 0, 1)
    push = direction * 0.08
    player.velocity += push
    player.pending_push += push
    player.slow_until_frame = max(player.slow_until_frame, frame + DEBRIS_SLOW_FRAMES)
    return True


def update_debris(session: SessionState) -> None:
    """Advance debris, apply harmless contact response and remove expired pieces."""

    active: list[Debris] = []
    for debris in session.debris:
        debris.update()
        if debris.remaining_frames <= 0:
            continue
        apply_debris_contact(session.player, debris, session.frame)
        active.append(debris)
    session.debris[:] = active[-MAX_DEBRIS:]


def update_respawns_for_building(session: SessionState, building: Building) -> None:
    """Advance one building's falling/absent/pending states in floor order."""

    for segment in building.all_segments():
        if (
            segment.status == FALLING
            and segment.destroyed_frame is not None
            and session.frame - segment.destroyed_frame >= DEBRIS_LIFETIME_FRAMES
        ):
            segment.status = ABSENT

    for segment in sorted(building.all_segments(), key=_respawn_sort_key):
        record = session.respawn_overrides.get(segment.segment_id)
        if record is None or session.frame < record.respawn_frame:
            continue
        if segment.status == FALLING:
            segment.status = ABSENT
        if segment.status not in (ABSENT, PENDING_RESPAWN):
            continue
        if building.can_restore(segment):
            segment.status = INTACT
            segment.destroyed_frame = None
            segment.respawn_frame = None
            session.respawn_overrides.pop(segment.segment_id, None)
        else:
            segment.status = PENDING_RESPAWN


def update_respawns(session: SessionState) -> None:
    """Apply independent respawn timers to every active building."""

    for building in session.world.all_buildings():
        update_respawns_for_building(session, building)


def demolish_segment(
    session: SessionState,
    building: Building,
    segment: BuildingSegment | None,
    cause: str = "click",
    player: Player | None = None,
) -> list[BuildingSegment]:
    """Apply direct demolition, then evaluate the building's support graph."""

    if segment is None or segment.status != INTACT:
        return []
    if cause == "contact" and player is not None:
        if not contact_is_ready(player, segment.segment_id, session.frame):
            return []
    changed: list[BuildingSegment] = []
    if _mark_segment_falling(session, building, segment):
        changed.append(segment)
    changed.extend(evaluate_support_cascade(session, building))
    return changed


def pick_nearest_segment(
    cursor: tuple[float, float],
    camera: Camera,
    target: Vector3,
    player_position: Vector3,
    candidates: Iterable[tuple[Building, BuildingSegment]],
    screen_size: tuple[int, int] = SCREEN_SIZE,
    context: ProjectionContext | None = None,
) -> tuple[Building, BuildingSegment] | None:
    """Pick the nearest projected visible intact segment under the cursor."""

    context = context or projection_context(camera, target, screen_size)
    best: tuple[float, tuple[Building, BuildingSegment]] | None = None
    for building, segment in candidates:
        if segment.status != INTACT:
            continue
        world_position = segment.world_position(building.origin)
        if world_position.distance_to(player_position) > MAX_PICK_DISTANCE:
            continue
        cuboid = segment.cuboid(building.origin)
        bounds = projected_cuboid_bounds(cuboid, context)
        if bounds is None:
            continue
        min_x, min_y, max_x, max_y, _ = bounds
        if not (min_x <= cursor[0] <= max_x and min_y <= cursor[1] <= max_y):
            continue
        hit_depths = [
            face.depth
            for face in project_cuboid_faces(
                cuboid,
                camera,
                target,
                screen_size,
                context=context,
            )
            if point_in_polygon(cursor, face.points)
        ]
        if not hit_depths:
            continue
        candidate = (min(hit_depths), (building, segment))
        if best is None or candidate[0] < best[0]:
            best = candidate
    return None if best is None else best[1]


def contacting_segments(session: SessionState) -> list[tuple[Building, BuildingSegment]]:
    """Return intact segments touching the player's current AABB."""

    player_box = session.player.aabb()
    return [
        (building, segment)
        for building, segment in session.world.static_segments()
        if player_box.intersects(segment.aabb(building.origin))
    ]


def _contacting_segment_entries(
    player_box: AABB,
    entries: Iterable[tuple[Building, BuildingSegment, AABB]],
) -> list[tuple[Building, BuildingSegment]]:
    """Filter precomputed static entries against the player's current AABB."""

    return [
        (building, segment)
        for building, segment, box in entries
        if player_box.intersects(box)
    ]


def update_gameplay(
    session: SessionState,
    movement: Vector3,
    jump_requested: bool = False,
) -> list[BuildingSegment]:
    """Run one fixed update, including streaming, player collision and contact demolition."""

    session.advance_frame()
    session.world.ensure_active(session.player.position, session.frame)
    static_entries = [
        (building, segment, segment.aabb(building.origin))
        for building, segment in session.world.static_segments()
    ]
    update_player(
        session.player,
        movement,
        (box for _, _, box in static_entries),
        session.frame,
        jump_requested,
    )
    changed: list[BuildingSegment] = []
    for building, segment in _contacting_segment_entries(
        session.player.aabb(), static_entries
    ):
        changed.extend(
            demolish_segment(
                session,
                building,
                segment,
                cause="contact",
                player=session.player,
            )
        )
    update_debris(session)
    update_respawns(session)
    return changed


def handle_game_event(
    session: SessionState,
    event: pygame.event.Event,
    screen_size: tuple[int, int] = SCREEN_SIZE,
) -> None:
    """Apply window, orbit and left-click demolition events before the update stage."""

    if event.type == pygame.QUIT:
        session.running = False
        session.clear_input_state()
    elif event.type == pygame.KEYDOWN:
        session.held_keys.add(event.key)
        if event.key == pygame.K_ESCAPE:
            session.running = False
            session.clear_input_state()
    elif event.type == pygame.KEYUP:
        session.held_keys.discard(event.key)
    elif event.type == pygame.WINDOWFOCUSLOST:
        session.clear_input_state()
    elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 3:
        session.camera.orbiting = True
    elif event.type == pygame.MOUSEBUTTONUP and event.button == 3:
        session.camera.orbiting = False
    elif event.type == pygame.MOUSEMOTION and session.camera.orbiting:
        session.camera.orbit(*event.rel)
    elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
        if session.camera.orbiting:
            return
        target = session.player.position + session.camera.target_offset
        picked = pick_nearest_segment(
            event.pos,
            session.camera,
            target,
            session.player.position,
            session.world.static_segments(),
            screen_size,
        )
        if picked is not None:
            demolish_segment(session, picked[0], picked[1], cause="click")


def create_render_surface(size: tuple[int, int] = SCREEN_SIZE) -> pygame.Surface:
    """Create a surface without opening a display, including in headless tests."""

    return pygame.Surface(size, flags=pygame.SRCALPHA)


def render_basic_scene(surface: pygame.Surface, session: SessionState) -> None:
    """Render the foundation scene used by the first playable checkpoint."""

    surface.fill((8, 10, 24))
    target = session.player.position + session.camera.target_offset
    context = projection_context(session.camera, target, surface.get_size())
    ground = Cuboid(Vector3(0, -0.12, 0), Vector3(160, 0.24, 160))
    draw_cuboid(surface, ground, session.camera, target, (20, 35, 58), context=context)
    avatar = Cuboid(session.player.position, session.player.size)
    draw_cuboid(
        surface,
        avatar,
        session.camera,
        target,
        (28, 220, 220),
        highlighted=True,
        context=context,
    )


def render_world(
    surface: pygame.Surface,
    session: SessionState,
    highlighted_segment_id: tuple[object, ...] | None = None,
) -> None:
    """Render the bounded active city, then the avatar and dynamic feedback."""

    surface.fill((8, 10, 24))
    target = (
        session.player.position
        + session.camera.target_offset
        + camera_shake_offset(session)
    )
    context = projection_context(session.camera, target, surface.get_size())
    ground = Cuboid(
        Vector3(session.player.position.x, -0.12, session.player.position.z),
        Vector3(200, 0.24, 200),
    )
    draw_cuboid(surface, ground, session.camera, target, (20, 35, 58), context=context)

    camera_position = session.camera.position(target)
    detailed: list[tuple[float, Building, BuildingSegment]] = []
    renderables: list[tuple[float, Cuboid, tuple[int, int, int], bool]] = []
    for building in session.world.all_buildings():
        building_distance = (building.origin - camera_position).length_squared()
        if building_distance > RENDER_DISTANCE**2:
            continue
        if building_distance <= DETAIL_RENDER_DISTANCE**2:
            for segment in building.all_segments():
                if segment.status != INTACT:
                    continue
                distance = (
                    segment.world_position(building.origin) - camera_position
                ).length_squared()
                detailed.append((distance, building, segment))
            continue
        intact_segments = [
            segment for segment in building.all_segments() if segment.status == INTACT
        ]
        if not intact_segments:
            continue
        # Distant buildings use one silhouette cuboid; selectable ranges stay
        # in the detailed band, keeping the software renderer responsive.
        renderables.append(
            (
                building_distance,
                Cuboid(
                    Vector3(
                        building.origin.x,
                        building.floor_count * FLOOR_HEIGHT * 0.5,
                        building.origin.z,
                    ),
                    Vector3(
                        building.width,
                        building.floor_count * FLOOR_HEIGHT,
                        building.depth,
                    ),
                ),
                building.color,
                False,
            )
        )

    detailed.sort(key=lambda item: item[0])
    selected = detailed[:MAX_RENDER_SEGMENTS]
    if highlighted_segment_id is not None and not any(
        segment.segment_id == highlighted_segment_id
        for _, _, segment in selected
    ):
        highlighted = next(
            (
                item
                for item in detailed[MAX_RENDER_SEGMENTS:]
                if item[2].segment_id == highlighted_segment_id
            ),
            None,
        )
        if highlighted is not None:
            selected.append(highlighted)
    renderables.extend(
        (
            distance,
            segment.cuboid(building.origin),
            building.color,
            segment.segment_id == highlighted_segment_id,
        )
        for distance, building, segment in selected
    )
    for _, cuboid, color, highlighted in sorted(
        renderables, key=lambda item: item[0], reverse=True
    ):
        draw_cuboid(
            surface,
            cuboid,
            session.camera,
            target,
            color,
            highlighted=highlighted,
            context=context,
        )

    for debris in session.debris:
        if hasattr(debris, "cuboid"):
            draw_cuboid(
                surface,
                debris.cuboid(),
                session.camera,
                target,
                (180, 210, 225),
                context=context,
            )

    draw_cuboid(
        surface,
        Cuboid(session.player.position, session.player.size),
        session.camera,
        target,
        (28, 220, 220),
        highlighted=True,
        context=context,
    )
    draw_effects(surface, session, context=context)
    draw_hud(surface, session)


def update_hud(
    session: SessionState,
    cursor: tuple[int, int],
    screen_size: tuple[int, int] = SCREEN_SIZE,
    refresh_target: bool = True,
) -> tuple[Building, BuildingSegment] | None:
    """Derive target and nearest respawn information for the HUD."""

    picked: tuple[Building, BuildingSegment] | None = None
    if refresh_target:
        target = session.player.position + session.camera.target_offset
        context = projection_context(session.camera, target, screen_size)
        picked = pick_nearest_segment(
            cursor,
            session.camera,
            target,
            session.player.position,
            session.world.static_segments(),
            screen_size,
            context=context,
        )
        session.hud.target_segment = None if picked is None else picked[1].segment_id
    session.hud.destroyed_count = session.destroyed_count
    remaining = [
        max(0, record.respawn_frame - session.frame)
        for record in session.respawn_overrides.values()
        if record.respawn_frame >= session.frame
    ]
    session.hud.respawn_remaining = (
        None if not remaining else (min(remaining) + FPS - 1) // FPS
    )
    return picked


def draw_effects(
    surface: pygame.Surface,
    session: SessionState,
    context: ProjectionContext | None = None,
) -> None:
    """Render lightweight flash and particle feedback from bounded effects."""

    target = session.player.position + session.camera.target_offset
    context = context or projection_context(session.camera, target, surface.get_size())
    for effect in session.effects:
        if effect.kind != "FLASH":
            if effect.kind != "PARTICLE":
                continue
            phase = effect.effect_id + effect.remaining_frames * 0.7
            particle_position = effect.position + Vector3(
                math.sin(phase * 1.7) * 0.45,
                0.4 + (MAX_EFFECT_LIFETIME_FRAMES - effect.remaining_frames) * 0.025,
                math.cos(phase * 1.3) * 0.45,
            )
            projected = _project_point_with_context(particle_position, context)
        else:
            projected = _project_point_with_context(effect.position, context)
        if projected is None:
            continue
        if effect.kind == "PARTICLE":
            radius = max(2, int(5 * effect.intensity * effect.remaining_frames / 24))
            pygame.draw.circle(
                surface,
                (255, 170, 90),
                (round(projected[0]), round(projected[1])),
                radius,
            )
            continue
        radius = max(4, int(18 * effect.intensity * effect.remaining_frames / 12))
        pygame.draw.circle(
            surface,
            (255, 240, 150),
            (round(projected[0]), round(projected[1])),
            radius,
            2,
        )


def camera_shake_offset(session: SessionState) -> Vector3:
    """Return a small deterministic visual-only camera shake vector."""

    offset = Vector3()
    for effect in session.effects:
        if effect.kind != "CAMERA_SHAKE":
            continue
        phase = effect.effect_id + effect.remaining_frames
        strength = effect.intensity * effect.remaining_frames / 10.0
        offset += Vector3(
            math.sin(phase * 2.1) * 0.05 * strength,
            math.cos(phase * 1.7) * 0.04 * strength,
            0.0,
        )
    return offset


def draw_hud(surface: pygame.Surface, session: SessionState) -> None:
    """Draw count, target, respawn countdown and the fixed controls hint."""

    if not pygame.font.get_init():
        pygame.font.init()
    font = pygame.font.Font(None, 24)
    title_font = pygame.font.Font(None, 32)
    width, height = surface.get_size()
    panel = pygame.Surface((width, 86), pygame.SRCALPHA)
    panel.fill((4, 8, 20, 205))
    surface.blit(panel, (0, 0))
    title = title_font.render("NEON CITY", True, (90, 240, 255))
    count = font.render(
        f"Unique demolished: {session.hud.destroyed_count}", True, (235, 245, 255)
    )
    target = font.render(
        "Target: " + ("ready" if session.hud.target_segment is not None else "none"),
        True,
        (255, 220, 120),
    )
    respawn_text = (
        "Respawn: --"
        if session.hud.respawn_remaining is None
        else f"Respawn: {session.hud.respawn_remaining}s"
    )
    respawn = font.render(respawn_text, True, (210, 220, 240))
    surface.blit(title, (16, 8))
    surface.blit(count, (170, 12))
    surface.blit(target, (16, 42))
    surface.blit(respawn, (170, 42))
    hint = font.render(session.hud.control_hint, True, (175, 190, 210))
    surface.blit(hint, (16, max(0, height - 30)))


def update_session_core(
    session: SessionState,
    movement: Vector3,
    jump_requested: bool = False,
) -> None:
    """Advance the foundation player and fixed-frame effect timers."""

    update_gameplay(session, movement, jump_requested)


def run_self_test() -> None:
    """Run deterministic, non-interactive checks for the complete core loop."""

    screen_size = (800, 600)
    camera = Camera()
    target = Vector3(0, 1, 0)
    visible = camera.position(target) + camera.forward(target) * 10
    assert project_point(visible, camera, target, screen_size) is not None
    assert project_point(camera.position(target) + Vector3(0, 0, -1), camera, target, screen_size) is None

    first_world = CityWorld(7)
    second_world = CityWorld(7)
    spawn = Vector3(0, PLAYER_HALF_HEIGHT, 0)
    first_world.ensure_active(spawn)
    second_world.ensure_active(spawn)
    assert len(first_world.active_chunks) == 9
    assert MIN_ACTIVE_BUILDINGS <= len(first_world.all_buildings()) <= MAX_ACTIVE_BUILDINGS
    assert first_world.chunk_layout((0, 0)) == second_world.chunk_layout((0, 0))
    original_layout = first_world.chunk_layout((0, 0))
    first_world.ensure_active(Vector3(CHUNK_SIZE * 2.1, PLAYER_HALF_HEIGHT, 0), frame=1)
    assert (2, 0) in first_world.active_chunks
    assert first_world.loaded_chunk_count <= MAX_LOADED_CHUNKS
    first_world.ensure_active(spawn, frame=2)
    assert first_world.chunk_layout((0, 0)) == original_layout

    player = Player(Vector3(0, PLAYER_HALF_HEIGHT, 0))
    assert player.try_jump()
    assert not player.try_jump()
    assert camera_relative_movement(Camera(), 1, 0).z > 0.99

    demo_session = create_session(world_seed=70)
    demo_building = Building.create(
        "self:0:0:0", Vector3(0, 0, 18), 6, 6, 4, (80, 200, 240)
    )
    demo_segment = demo_building.segment((demo_building.building_id, 1, 0, "column"))
    assert demo_segment is not None
    projected = project_point(
        demo_segment.world_position(demo_building.origin),
        demo_session.camera,
        demo_session.player.position + demo_session.camera.target_offset,
        screen_size,
    )
    assert projected is not None
    picked = pick_nearest_segment(
        (projected[0], projected[1]),
        demo_session.camera,
        demo_session.player.position + demo_session.camera.target_offset,
        demo_session.player.position,
        [(demo_building, demo_segment)],
        screen_size,
    )
    assert picked is not None and picked[1].segment_id == demo_segment.segment_id
    changed = demolish_segment(demo_session, demo_building, demo_segment)
    assert demo_building.segment((demo_building.building_id, 2, 0, "column")).status == FALLING
    assert changed and demo_session.destroyed_count == len(demo_session.counted_segment_keys)

    demo_session.frame = demo_segment.respawn_frame or RESPAWN_FRAMES
    update_respawns_for_building(demo_session, demo_building)
    assert demo_segment.status == INTACT
    previous_count = demo_session.destroyed_count
    demolish_segment(demo_session, demo_building, demo_segment)
    assert demo_session.destroyed_count == previous_count

    for _ in range(MAX_EFFECTS + 5):
        demo_session.add_effect("FLASH", Vector3())
    assert len(demo_session.effects) == MAX_EFFECTS
    for _ in range(MAX_DEBRIS + 5):
        demo_session.add_debris(Debris(("self",), Vector3()))
    assert len(demo_session.debris) == MAX_DEBRIS
    print("NEON CITY self-test: all core rules ok")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="NEON CITY 3D demolition sandbox")
    parser.add_argument(
        "--self-test",
        action="store_true",
        help="run deterministic headless checks and exit",
    )
    args = parser.parse_args(argv)
    if args.self_test:
        run_self_test()
        return 0

    pygame.init()
    try:
        screen = pygame.display.set_mode(SCREEN_SIZE, pygame.RESIZABLE)
        pygame.display.set_caption("NEON CITY")
        clock = pygame.time.Clock()
        session = create_session()
        while session.running:
            jump_requested = False
            for event in pygame.event.get():
                handle_game_event(session, event, screen.get_size())
                if event.type == pygame.KEYDOWN and event.key == pygame.K_SPACE:
                    jump_requested = True

            if not session.running:
                break
            keys = session.held_keys
            movement = camera_relative_movement(
                session.camera,
                float(pygame.K_w in keys) - float(pygame.K_s in keys),
                float(pygame.K_d in keys) - float(pygame.K_a in keys),
            )
            update_session_core(session, movement, jump_requested)
            cursor = pygame.mouse.get_pos()
            update_hud(
                session,
                cursor,
                screen.get_size(),
                refresh_target=session.frame % HUD_TARGET_REFRESH_FRAMES == 0,
            )
            render_world(screen, session, session.hud.target_segment)
            pygame.display.flip()
            clock.tick(FPS)
    finally:
        pygame.quit()
    return 0


if __name__ == "__main__":
    sys.exit(main())
