# Glossary — Decoder Ring

_Last updated: 2026-05-27_

## Models & Tools

| Term | Meaning |
|------|---------|
| **Gemma4** | Local LLM used for code execution (via e2b sandbox). Claude plans; Gemma4 writes code. |
| **e2b** | Code execution sandbox where Gemma4 runs |
| **Ollama** | Local LLM runner (alternative path; config.toml sets the model) |

## Personal Brand Subsystems

| Term | Meaning |
|------|---------|
| **narrative_warehouse** | Story storage subsystem — holds all `story_nodes` |
| **instagram_frameworks** | Instagram content generation subsystem |
| **linkedin_frameworks** | LinkedIn content generation subsystem |
| **story_nodes** | Individual story units extracted from diary entries |
| **worth_score** | Quality score for story_nodes. Floor is `0.70` (config-driven) |
| **Notion Diary Fetcher** | Pipeline that fetches diary pages from Notion and extracts stories |
| **Stage1 extractor** | Claude Sonnet-based extractor for 82 unprocessed diary pages |
| **pratfall injection** | Planned Phase 2 feature: adding vulnerability/failure moments to posts |

## TurboBaba Terms

| Term | Meaning |
|------|---------|
| **TB** | TurboBaba project identifier (from Plane) |
| **BYO AI** | "Bring Your Own AI" — markdown export + prompt templates so users bring their own LLM |
| **PWA** | Progressive Web App shell for TurboBaba |
| **RLS** | Row Level Security — Supabase auth layer for multi-user data isolation |
| **Strava** | Primary data integration for TurboBaba (workouts, runs, hikes) |

## Infrastructure

| Term | Meaning |
|------|---------|
| **uv** | Python package manager (replaces pip/poetry). Use `uv sync` to install. |
| **shared** | Shared Python package at `personal_brand/shared/shared/`. Contains the logger. |
| **Blueprint** | Planning artifact saved to `handoff/blueprint_vX.X_[feature].md` |
