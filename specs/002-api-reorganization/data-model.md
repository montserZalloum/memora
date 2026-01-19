# Data Model: API Module Reorganization

**Date**: 2026-01-19
**Feature**: 002-api-reorganization

## Overview

**No data model changes required.**

This feature is a pure code reorganization (refactoring) of the `api.py` file into a modular package structure. No database entities, fields, relationships, or state transitions are affected.

## Existing Entities (Reference Only)

The following DocTypes are accessed by the API functions being reorganized. Their schemas remain unchanged:

| DocType | Used By Module(s) |
|---------|-------------------|
| `Player Profile` | subjects, profile, srs, leaderboard, store, onboarding |
| `Game Academic Plan` | subjects, map, onboarding |
| `Game Subject` | subjects, map, profile, leaderboard, store |
| `Game Unit` | map |
| `Game Topic` | map, srs |
| `Game Lesson` | map, srs |
| `Game Learning Track` | subjects, map, store |
| `Game Stage` | srs |
| `Player Memory Tracker` | srs, profile |
| `Gameplay Session` | map, srs, profile, leaderboard |
| `Game Player Subscription` | _utils (shared) |
| `Game Subscription Season` | _utils, onboarding |
| `Game Sales Item` | store |
| `Game Purchase Request` | store |
| `Game Academic Grade` | onboarding |
| `Game Academic Stream` | onboarding |
| `Player Subject Score` | profile, leaderboard |

## Conclusion

No data model artifacts to generate. Proceed to quickstart.md.
