# Memora Documentation

Welcome to the Memora application documentation. Memora is a gamified learning platform built on the Frappe framework that uses spaced repetition systems (SRS) to help students master academic content through interactive gameplay.

## Table of Contents

- [Overview](#overview)
- [Quick Start](#quick-start)
- [Architecture](#architecture)
- [Core Concepts](#core-concepts)
- [Documentation Sections](#documentation-sections)
- [Development](#development)
- [Testing](#testing)

## Overview

Memora is an educational gamification platform that combines:

- **Spaced Repetition System (SRS)**: Optimizes learning by scheduling reviews at optimal intervals
- **Gamification**: Engages students through points, levels, quests, and leaderboards
- **Adaptive Learning**: AI-powered question generation and difficulty adjustment
- **Multi-Tenant Architecture**: Supports multiple academic institutions with customized content
- **High-Performance Caching**: Redis-based caching for sub-100ms response times

### Key Features

- **Interactive Learning Map**: Visual progression through topics and lessons
- **Review Sessions**: Daily spaced repetition practice with due questions
- **Daily Quests**: Engaging challenges to maintain motivation
- **Leaderboards**: Competitive rankings across subjects and time periods
- **Store System**: In-app purchases for subscriptions and content bundles
- **Multi-Subject Support**: Mathematics, Science, Languages, and more
- **Academic Tracks**: Grade-specific learning paths aligned with curricula

## Quick Start

### Installation

```bash
cd $PATH_TO_YOUR_BENCH
bench get-app $URL_OF_THIS_REPO --branch develop
bench install-app memora
```

### Setup

After installation, the following tasks run automatically:

1. **Infrastructure Setup**: Configures database partitions and indexes
2. **Review System**: Initializes SRS tracking tables
3. **Partitioning**: Sets up season-based database partitioning

### Development Setup

```bash
cd apps/memora
pre-commit install
```

## Architecture

### Technology Stack

- **Backend**: Python 3.11+ with Frappe Framework
- **Database**: PostgreSQL with LIST COLUMNS partitioning
- **Cache**: Redis for high-performance SRS operations
- **Frontend**: JavaScript (Vanilla) with Frappe Desk integration

### System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Client Application                       │
│                   (Web/Mobile Interface)                     │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                   API Layer (modular)                        │
│  - subjects.py  - sessions.py  - reviews.py  - srs.py       │
│  - profile.py   - quests.py   - leaderboard.py  - store.py   │
└────────────────────────┬────────────────────────────────────┘
                         │
         ┌───────────────┼───────────────┐
         │               │               │
         ▼               ▼               ▼
┌─────────────────┐ ┌──────────┐ ┌─────────────────┐
│  Redis Cache    │ │PostgreSQL│ │  Background     │
│  (SRS Data)     │ │(Master)  │ │  Services       │
│                 │ │          │ │  - Archiver     │
│  - <100ms reads │ │- Partit. │ │  - Reconcile    │
│  - Safe Mode    │ │- Indexed │ │  - Persistence  │
└─────────────────┘ └──────────┘ └─────────────────┘
```

### Module Organization

```
memora/
├── api/                    # Modular API endpoints
│   ├── __init__.py        # Public API gateway
│   ├── utils.py           # Shared utilities
│   ├── subjects.py        # Subject & track management
│   ├── map_engine.py      # Learning map navigation
│   ├── sessions.py        # Gameplay sessions
│   ├── reviews.py         # Review sessions (SRS)
│   ├── srs.py             # SRS algorithms & admin
│   ├── profile.py         # Player profiles
│   ├── quests.py          # Daily quests
│   ├── leaderboard.py     # Leaderboards
│   ├── onboarding.py      # User onboarding
│   └── store.py           # In-app store
├── services/               # Business logic services
│   ├── srs_redis_manager.py      # Redis operations
│   ├── srs_persistence.py        # Async DB writes
│   ├── srs_archiver.py           # Season archival
│   ├── srs_reconciliation.py    # Cache consistency
│   └── partition_manager.py     # DB partitioning
├── memora/doctype/         # Frappe DocTypes (data models)
│   ├── player_profile/
│   ├── player_memory_tracker/
│   ├── gameplay_session/
│   ├── game_subject/
│   ├── game_topic/
│   ├── game_lesson/
│   └── ...
├── patches/                # Database migrations
├── tests/                  # Test suite
└── public/                 # Static assets
```

## Core Concepts

### Spaced Repetition System (SRS)

Memora uses an optimized SRS algorithm to schedule reviews:

- **Memory Tracker**: Records each player's interaction with every question
- **Due Calculation**: Determines which questions need review based on performance
- **Interval Adjustment**: Adjusts review intervals based on recall accuracy
- **Redis Caching**: Fast retrieval of due questions (<100ms)
- **Safe Mode**: Fallback to database when Redis is unavailable

### Gamification Elements

- **XP (Experience Points)**: Earned through completing lessons and reviews
- **Levels**: Progression based on accumulated XP
- **Streaks**: Consecutive days of activity
- **Daily Quests**: Specific challenges with rewards
- **Leaderboards**: Rankings by subject, grade, or global
- **Achievements**: Special accomplishments and milestones

### Academic Structure

```
Academic Grade (e.g., Grade 10)
└── Academic Stream (e.g., Science)
    └── Academic Plan (e.g., CBSE, ICSE)
        └── Subject (e.g., Mathematics)
            └── Topic (e.g., Algebra)
                └── Lesson (e.g., Linear Equations)
                    └── Questions
```

### Subscription Model

- **Subscription Season**: Time-based access period (e.g., "2024-2025")
- **Subscription Access**: Controls content access per season
- **Purchase Requests**: In-app purchase flow
- **Content Bundles**: Grouped content for sale

## Documentation Sections

### API Documentation
- **[API Overview](api/README.md)**: Complete API reference with all endpoints
- **[SRS API](api/srs.md)**: Spaced repetition system endpoints
- **[Session API](api/sessions.md)**: Gameplay session management
- **[Review API](api/reviews.md)**: Review session endpoints

### Data Models
- **[Main DocTypes](business/01_MAIN_DOCTYPES.md)**: Core data entities
- **[DocType Explanations](business/02_MAIN_DOCTYPES_EXPLANATION.md)**: Detailed entity descriptions
- **[Player Profile](doctypes/player_profile.md)**: User profile structure
- **[Memory Tracker](doctypes/memory_tracker.md)**: SRS tracking system

### Services
- **[SRS Services](services/srs.md)**: Spaced repetition services
- **[Redis Manager](services/redis_manager.md)**: Cache management
- **[Archiver](services/archiver.md)**: Data archival process
- **[Reconciliation](services/reconciliation.md)**: Cache consistency

### Development
- **[Development Guide](development/README.md)**: Setup and best practices
- **[Testing Guide](development/testing.md)**: Test suite and testing practices
- **[Unit Testing Plan](unit_testing_plan.md)**: Testing strategy
- **[Unit Testing Scenarios](unit_testing_scenarious.md)**: Test cases

### Features
- **[Topic Review Logic](TOPIC_REVIEW_LOGIC.md)**: Review algorithm details
- **[Cancel Subscription](features_to_add/cancel_subscription.md)**: Subscription management
- **[User Session](features_to_add/user_session.md)**: Session handling
- **[Tracker](features_to_add/tracker.md)**: Progress tracking

## Development

### Code Style

- **Python**: Follow PEP 8 conventions
- **JavaScript**: ESLint configuration in `.eslintrc`
- **Formatting**: Prettier for JavaScript/JSON

### Pre-commit Hooks

The project uses pre-commit for code quality:

```bash
pre-commit install
```

Tools configured:
- `ruff`: Python linting and formatting
- `eslint`: JavaScript linting
- `prettier`: Code formatting
- `pyupgrade`: Python syntax modernization

### Module Guidelines

- **API Modules**: Max 400 lines per file
- **Domain Separation**: Each API module handles one domain
- **Cross-module Imports**: Minimize dependencies between modules
- **Service Layer**: Business logic in services, not in API layer

### Adding New Features

1. Create feature specification in `specs/`
2. Implement API endpoints in appropriate module
3. Add DocTypes if needed
4. Create services for business logic
5. Write tests
6. Update documentation

## Testing

### Running Tests

```bash
# Run all tests
pytest memora/tests/

# Run specific test file
pytest memora/tests/test_srs_archiver.py

# Run with coverage
pytest --cov=memora memora/tests/
```

### Test Structure

```
memora/tests/
├── test_srs_archiver.py       # Archiver service tests
├── test_srs_redis.py          # Redis manager tests
├── test_srs_reconciliation.py # Reconciliation tests
└── performance_test.py       # Performance benchmarks
```

### Testing Best Practices

- Write unit tests for all service functions
- Test API endpoints with mock data
- Verify SRS algorithm correctness
- Test cache consistency
- Performance test critical paths

## Performance

### SRS System Performance

- **Redis Cache**: <100ms response time for review retrieval
- **Safe Mode**: <500ms with rate limiting
- **Async Persistence**: <500ms confirmation, background DB write
- **Cache Rebuild**: Background job with progress tracking

### Database Optimization

- **Partitioning**: Season-based LIST COLUMNS partitioning
- **Indexes**: Composite indexes for common queries
- **Archival**: Automatic archival of old seasons
- **Cleanup**: Weekly deletion of records older than 3 years

## Background Jobs

Scheduled tasks configured in [`memora/hooks.py`](../memora/hooks.py:29):

| Job | Frequency | Purpose |
|-----|-----------|---------|
| `process_auto_archive` | Daily | Archive seasons marked for auto-archive |
| `flag_eligible_for_deletion` | Weekly | Flag archived records for deletion |
| `reconcile_cache_with_database` | Daily | Check cache consistency |

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Write tests
5. Run pre-commit hooks
6. Submit a pull request

## License

MIT License - See [license.txt](../license.txt) for details

## Support

For issues and questions:
- Email: dev@corex.com
- Documentation: See specific sections above
- API Reference: Check API documentation

---

**Last Updated**: 2026-01-20
**Version**: 1.0
