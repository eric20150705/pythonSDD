<!--
Sync Impact Report
- Version change: Unversioned scaffold → 1.0.0
- Modified principles: Five scaffold placeholders → five project-specific principles
- Added sections: Project Constraints; Development Workflow and Quality Gates
- Removed sections: None; the scaffold sections were replaced with concrete project guidance
- Follow-up TODOs: None
-->

# Python Pygame Learning Project Constitution

## Core Principles

### I. Playable Increment First

Every feature MUST begin with the smallest playable result that can be seen, controlled,
or otherwise verified in the game. A feature is complete only when its success condition,
player input, visible feedback, and failure or boundary behavior are defined. New work MUST
extend the existing playable game in small steps instead of combining many unverified ideas
into one large change.

Rationale: The project has progressed from basic functions and a window to bricks, a paddle,
a ball, collisions, power-ups, particles, and win/loss states. Continuing with short vertical
slices keeps that progress understandable and makes mistakes easier to locate.

### II. Clear Python Fundamentals

Project code MUST favor readable variables, named constants, small functions, and simple
classes with one understandable responsibility. A new abstraction MUST solve a concrete
problem in the current feature; patterns, frameworks, and indirection MUST NOT be added only
to appear sophisticated. Existing code MAY be improved gradually, but a feature MUST NOT be
blocked by a broad rewrite that is unrelated to its behavior.

Rationale: The current code demonstrates effective use of Python fundamentals and Pygame
objects. The project should strengthen those skills before requiring advanced architecture.

### III. Recognizable Game-Loop Responsibilities

The main loop MUST keep event handling, game-state updates, collision and effect rules, and
rendering in clearly identifiable sections or functions. Classes MUST keep their own state
and behavior together where that improves clarity. A change that adds a new game rule MUST
identify where the rule is updated, how it affects state, and how the player sees the result.

Rationale: The project already uses Pygame's event loop and classes such as `Brick`, `Paddle`,
and `Ball`. Making responsibilities explicit will allow more features without losing control
of the program as the game grows.

### IV. Verify Before Expanding

Before a feature is considered complete, the author MUST run a syntax or import check for the
changed Python files and perform a manual smoke test of the affected controls and game states.
Collision, scoring, timing, and other repeatable rules SHOULD have small automated checks once
they are separated from rendering. A failed check MUST be fixed or recorded as an explicit
known limitation before the next feature is started.

Rationale: The project is currently visual and interactive, so manual play is essential, but
repeatable checks will become increasingly valuable as the rules and effects multiply.

### V. Safe, Incremental Refactoring

Refactoring MUST preserve a runnable version of the game and MUST be kept separate from new
gameplay work unless the feature cannot be implemented safely without it. Before moving logic,
the current behavior MUST be recorded through a smoke-test checklist or automated check. When
a file contains several unrelated responsibilities, the next suitable change SHOULD extract
one responsibility at a time rather than rewrite the whole project.

Rationale: D2 has grown into a substantial single-file game. Small extractions reduce risk and
build maintainable habits without dismissing the working code that already exists.

## Project Constraints

- The project MUST use Python and Pygame Community Edition as its primary runtime stack.
- Runtime dependencies MUST be declared in `requirements.txt`; a new dependency MUST include
  a short reason in the relevant plan or project documentation.
- Existing gameplay targets a 60 FPS loop unless a feature explicitly defines and verifies a
  different timing model.
- New features MUST remain understandable to a learner who can read functions, classes,
  constants, lists, dictionaries, and basic object state. More advanced techniques MAY be
  introduced when they solve a demonstrated problem and are explained in the plan.
- Temporary editor output, generated caches, credentials, and machine-specific files MUST NOT
  be treated as project source or committed as part of a feature.

## Development Workflow and Quality Gates

1. Describe the player-facing behavior, controls, states, and success criteria before coding.
2. Break the work into one playable slice and identify the functions, classes, or constants it
   will touch.
3. Implement the smallest change that satisfies the slice, keeping input, update, collision,
   and drawing responsibilities recognizable.
4. Run `python -m compileall` on the affected project directories and manually exercise the
   changed path, including at least one boundary or failure case.
5. Add or update a focused automated check when the feature contains repeatable non-visual
   rules such as scoring, collision outcomes, timers, or state transitions.
6. Review the change against this constitution before starting the next slice. Any exception
   MUST be documented with its reason and the behavior it protects.

## Governance

This constitution defines the project's development priorities and takes precedence over
convenience-based coding habits. Feature specifications, plans, task lists, and code reviews
MUST be checked against these principles. When a requirement conflicts with this constitution,
the conflict MUST be resolved explicitly in the relevant design artifact before implementation.

The project owner may amend this constitution when the project's learning goals, technology,
or maintenance needs change. Each amendment MUST update the Sync Impact Report, explain the
reason for the change, update the semantic version, and set the Last Amended date. An amendment
that removes or redefines a principle is a MAJOR version; a new principle or materially wider
requirement is a MINOR version; wording clarifications and non-semantic corrections are a PATCH
version.

Every feature review MUST confirm that the implementation has a defined playable outcome,
passes the applicable syntax and smoke checks, and records any accepted limitation. The
constitution MUST be revisited when a feature repeatedly violates a rule or when the rule no
longer supports the project's learning goals; code MUST NOT silently bypass it.

**Version**: 1.0.0 | **Ratified**: 2026-08-26 | **Last Amended**: 2026-08-26
