# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Documentation rule

**Always update documentation when code changes.** After any code change, check whether `CLAUDE.md`, `README.md`, `Dockerfile`, `docker-compose.yml`, `requirements.txt`, and `.env.example` need updating and apply those updates in the same step. Do not wait to be asked.

## Architectural decisions — do NOT change unilaterally

**Never change the AI model, model family, or core architecture without explicit user instruction.** The choice of SAM 3.1 over SAM 2 or any other model is the user's decision. If a model integration fails, diagnose and fix the integration — do not silently swap the model.

## What this project is

**ArtSegment** — a desktop painting-reference tool for artists. It uses Meta's **SAM 3.1** AI model to segment an image into semantically meaningful zones via a text prompt, then analyzes each zone for dominant color, tonal structure (light/shadow), and edges. Output is a flattened PNG or a vector SVG the artist can use as a painting guide.

The core insight comes from GIS: just as satellite images are segmented into land-cover objects with zonal statistics, a painting can be broken into color zones, each with a dominant hue to mix.

## Documentation

Detailed reference lives in `docs/`:

- [`docs/architecture.md`](docs/architecture.md) — file tree, processing pipeline, key design decisions
- [`docs/setup.md`](docs/setup.md) — prerequisites, install methods (Windows / manual / Docker), Windows-specific notes
- [`docs/dependencies.md`](docs/dependencies.md) — dependency constraints, SAM3 Windows patch system
- [`docs/theme.md`](docs/theme.md) — QSS color tokens, frameless window styling
