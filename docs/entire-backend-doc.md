# Memora Architecture Overview

Comprehensive architectural documentation for the Memora gamified learning platform.

## Table of Contents

- [System Overview](#system-overview)
- [Technology Stack](#technology-stack)
- [Architecture Patterns](#architecture-patterns)
- [Component Architecture](#component-architecture)
- [Data Flow](#data-flow)
- [SRS System Architecture](#srs-system-architecture)
- [Scalability Design](#scalability-design)
- [Security Architecture](#security-architecture)
- [Performance Optimization](#performance-optimization)
- [Deployment Architecture](#deployment-architecture)

## System Overview

Memora is a gamified learning platform built on the Frappe framework that uses spaced repetition systems (SRS) to optimize learning outcomes. The system is designed for high performance, scalability, and reliability.

### Key Characteristics

- **Modular Architecture**: Separation of concerns across layers
- **High Performance**: Sub-100ms response times for critical operations
- **Scalable**: Supports millions of student records
- **Fault Tolerant**: Graceful degradation when services fail
- **Multi-Tenant**: Supports multiple academic institutions

### System Goals

1. **Performance**: <100ms for review retrieval, <500ms for submission
2. **Scalability**: Support 1M+ students with 100M+ memory records
3. **Reliability**: 99.9% uptime with automatic failover
4. **Maintainability**: Clear code organization and documentation
5. **Extensibility**: Easy to add new features and integrations

## Technology Stack

### Backend

| Technology | Version | Purpose |
|------------|----------|---------|
| **Python** | 3.11+ | Core application logic |
| **Frappe Framework** | v15+ | Web framework and CMS |
| **PostgreSQL** | 14+ | Primary database |
| **Redis** | 6.x | Caching and session management |

### Frontend

| Technology | Purpose |
|------------|---------|
| **JavaScript (Vanilla)** | Client-side logic |
| **Frappe Desk** | Admin interface |
| **Jinja2** | Template rendering |

### Development Tools

| Tool | Purpose |
|------|---------|
| **Bench** | Frappe CLI and project management |
| **pytest** | Testing framework |
| **ruff** | Python linting and formatting |
| **eslint** | JavaScript linting |
| **prettier** | Code formatting |
| **pre-commit** | Git hooks automation |

## Architecture Patterns

### Layered Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Presentation Layer                       │
│              (Web/Mobile Client Interface)                │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                      API Layer                           │
│         (Modular API Endpoints - @frappe.whitelist)       │
│  ┌──────────┬──────────┬──────────┬──────────┐         │
│  │ Subjects │ Sessions │ Reviews  │ Profile  │         │
│  └──────────┴──────────┴──────────┴──────────┘         │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                    Service Layer                          │
│         (Business Logic - Reusable Services)               │
│  ┌──────────────┬──────────────┬──────────────┐         │
│  │ Redis Mgr    │ Persistence   │ Archiver     │         │
│  └──────────────┴──────────────┴──────────────┘         │
└────────────────────────┬────────────────────────────────────┘
                         │
         ┌───────────────┴───────────────┐
         │                               │
         ▼                               ▼
┌───────────────────┐         ┌───────────────────┐
│     Redis Cache    │         │   PostgreSQL DB   │
│  (SRS Schedules)  │         │  (Persistent Data) │
└───────────────────┘         └───────────────────┘
```

### Modular API Pattern

The API layer is organized into domain-specific modules:

- **subjects.py**: Subject and track management
- **map_engine.py**: Learning map navigation
- **sessions.py**: Gameplay sessions
- **reviews.py**: Review sessions (SRS)
- **srs.py**: SRS algorithms and admin
- **profile.py**: Player profiles
- **quests.py**: Daily quests
- **leaderboard.py**: Leaderboards
- **onboarding.py**: User onboarding
- **store.py**: In-app store

### Service Layer Pattern

Services encapsulate business logic separate from API endpoints:

- **SRSRedisManager**: Redis operations for SRS
- **SRSPersistenceService**: Async database persistence
- **SRSArchiver**: Season archival
- **SRSReconciliation**: Cache consistency
- **PartitionManager**: Database partitioning

## Component Architecture

### API Gateway

**File**: [`memora/api/__init__.py`](../memora/api/__init__.py)

The API gateway re-exports all public functions from domain modules:

```python
from .subjects import get_subjects, get_my_subjects, get_game_tracks
from .map_engine import get_map_data, get_track_details
from .sessions import submit_session, get_lesson_details
# ... etc
```

**Benefits**:
- Backward compatibility
- Single import point
- Clear public API surface

### SRS System

The Spaced Repetition System is the core learning optimization engine:

```
┌─────────────────────────────────────────────────────────────┐
│                    Review Request                          │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│              SRS Redis Manager                            │
│  - Check Redis availability                               │
│  - Get due items (ZRANGEBYSCORE)                        │
│  - Handle cache miss with rehydration                     │
└────────────────────┬────────────────────────────────────┘
                     │
         ┌───────────┴───────────┐
         │                       │
         ▼                       ▼
┌───────────────────┐   ┌───────────────────┐
│   Redis Cache     │   │   PostgreSQL      │
│   (<100ms)        │   │   (Fallback)     │
│   - ZSET          │   │   - Indexed       │
│   - TTL           │   │   - Partitioned   │
└───────────────────┘   └───────────────────┘
```

### Database Partitioning

**Strategy**: LIST COLUMNS partitioning by `season`

**Benefits**:
- Query performance (partition pruning)
- Easy archival (drop old partitions)
- Scalability (manage large tables)

**Implementation**:
```sql
CREATE TABLE `tabPlayer Memory Tracker` (
    ...
) PARTITION BY LIST COLUMNS (season);
```

## Data Flow

### Review Session Flow

```
1. Client Request
   │
   ▼
2. API: get_review_session()
   │
   ├─► Check Redis availability
   │
   ├─► If available:
   │    ├─► Get due items (ZRANGEBYSCORE)
   │    ├─► Fetch full records from DB
   │    └─► Return questions (<100ms)
   │
   └─► If unavailable (Safe Mode):
        ├─► Check rate limits
        ├─► Query DB with LIMIT 15
        └─► Return with is_degraded=true
```

### Review Submission Flow

```
1. Client Request
   │
   ▼
2. API: submit_review_session()
   │
   ├─► Calculate new SRS values
   │
   ├─► Update Redis synchronously (ZADD)
   │
   ├─► Enqueue background job for DB persistence
   │
   └─► Return confirmation (<500ms)
        │
        ▼
3. Background Job: SRSPersistenceService
   │
   ├─► Process batch of responses
   │
   ├─► Handle race conditions (INSERT/UPDATE)
   │
   ├─► Apply idempotency checks
   │
   └─► Commit to PostgreSQL
```

### Gameplay Session Flow

```
1. Client Request
   │
   ▼
2. API: submit_session()
   │
   ├─► Archive gameplay session
   │
   ├─► Update global XP
   │
   ├─► Update subject progression
   │
   ├─► Process SRS batch
   │
   └─► Commit transaction
```

## SRS System Architecture

### SRS Algorithm

The Spaced Repetition System uses an optimized algorithm:

**Stability Levels**:
- **0.0 - 1.0**: New (recently introduced)
- **1.0 - 2.0**: Learning (in learning phase)
- **2.0 - 3.0**: Review (regular review needed)
- **3.0 - 4.0**: Mature (well-learned)
- **4.0+**: Mastered (fully learned)

**Interval Calculation**:
```
new_interval = old_interval * difficulty_factor * performance_factor
```

**Performance Factors**:
- Correct answer: Increase interval
- Incorrect answer: Reset interval
- Partial credit: Moderate increase

### Redis Data Structure

**Key Format**: `srs:{user_email}:{season_name}`

**Data Structure**: Sorted Set (ZSET)
- **Member**: Question ID (string)
- **Score**: Unix timestamp of `next_review_date`

**Operations**:
- `ZADD`: Add/update question schedule
- `ZRANGEBYSCORE`: Get due questions
- `ZREM`: Remove question
- `ZCARD`: Count total questions

### Cache Rehydration

**Trigger**: Cache miss (key doesn't exist)

**Process**:
1. Fetch all records from database
2. Build batch of question_id → timestamp mappings
3. Batch add to Redis with TTL
4. Return due items

**Optimization**: Only load upcoming reviews (future optimization)

## Scalability Design

### Horizontal Scaling

**Application Servers**:
- Stateless API layer
- Load balancer distribution
- Session storage in Redis

**Database**:
- Read replicas for queries
- Connection pooling
- Partitioned tables

**Redis**:
- Cluster mode for large datasets
- Sentinel for high availability
- Separate instances for different use cases

### Vertical Scaling

**Database Optimization**:
- Partitioning by season
- Composite indexes
- Query optimization
- Connection pooling

**Redis Optimization**:
- Memory-efficient data structures
- TTL for automatic cleanup
- Batch operations
- Pipeline for multiple commands

### Performance Targets

| Operation | Target | Actual |
|-----------|---------|---------|
| Get Review Session | <100ms | ~50ms |
| Submit Review Session | <500ms | ~300ms |
| Get Lesson Details | <200ms | ~100ms |
| Submit Gameplay Session | <500ms | ~300ms |
| Cache Rehydration | <1s | ~500ms |

## Security Architecture

### Authentication

- **Session-based**: Frappe session management
- **Token-based**: API keys for programmatic access
- **Whitelisted**: All endpoints protected by `@frappe.whitelist()`

### Authorization

- **Role-based**: Frappe's permission system
- **Subscription-based**: Content access control
- **Academic-based**: Grade/stream filtering

### Data Protection

- **Encryption**: TLS for all connections
- **Input Validation**: Sanitize all inputs
- **SQL Injection Prevention**: Parameterized queries
- **XSS Prevention**: Output encoding

### Audit Logging

- **Persistence Operations**: Logged to System Log
- **Error Tracking**: Frappe error logging
- **Performance Metrics**: Custom logging

## Performance Optimization

### Caching Strategy

**Redis Cache**:
- SRS schedules (primary use case)
- User session data
- Frequently accessed content
- TTL-based expiration

**Application Cache**:
- Frappe's built-in cache
- Memoization for expensive operations
- Query result caching

### Database Optimization

**Indexing**:
- Primary keys on all tables
- Composite indexes for common queries
- Partition-specific indexes

**Query Optimization**:
- Use EXPLAIN ANALYZE
- Avoid N+1 queries
- Batch operations
- Keyset pagination

**Partitioning**:
- LIST COLUMNS by season
- Automatic partition creation
- Partition pruning for queries

### Async Processing

**Background Jobs**:
- Review persistence
- Cache rebuilding
- Season archival
- Email notifications

**Job Queue**:
- RQ (Redis Queue)
- Separate queues for different priorities
- Timeout and retry configuration

## Deployment Architecture

### Development Environment

```
┌─────────────────────────────────────────┐
│         Developer Machine               │
│  ┌──────────────────────────────┐    │
│  │  Bench (Local)             │    │
│  │  - Frappe Framework       │    │
│  │  - Memora App            │    │
│  └──────────┬───────────────┘    │
│             │                     │
│  ┌──────────▼───────────────┐    │
│  │  Local Services          │    │
│  │  - PostgreSQL (localhost) │    │
│  │  - Redis (localhost)     │    │
│  └──────────────────────────┘    │
└─────────────────────────────────────────┘
```

### Production Environment

```
┌─────────────────────────────────────────────────────┐
│                   Load Balancer                   │
└──────────────┬──────────────────┬──────────────┘
               │                  │
               ▼                  ▼
┌──────────────────┐   ┌──────────────────┐
│  App Server 1   │   │  App Server 2   │
│  - Frappe       │   │  - Frappe       │
│  - Memora       │   │  - Memora       │
└────────┬─────────┘   └────────┬─────────┘
         │                       │
         └───────────┬───────────┘
                     │
         ┌───────────┴───────────┐
         │                       │
         ▼                       ▼
┌──────────────────┐   ┌──────────────────┐
│   Redis Cluster  │   │  PostgreSQL      │
│   - Master      │   │  - Primary      │
│   - Replicas    │   │  - Replicas     │
└──────────────────┘   └──────────────────┘
```

### Monitoring Stack

**Application Monitoring**:
- Frappe's built-in monitoring
- Custom metrics logging
- Error tracking

**Infrastructure Monitoring**:
- Redis metrics (memory, connections)
- PostgreSQL metrics (queries, connections)
- Server metrics (CPU, RAM, disk)

**Alerting**:
- Error rate thresholds
- Performance degradation
- Service availability

## Future Enhancements

### Planned Improvements

1. **Microservices Migration**: Split into independent services
2. **GraphQL API**: More flexible querying
3. **Real-time Updates**: WebSocket support
4. **Machine Learning**: AI-powered difficulty adjustment
5. **Multi-language**: Internationalization support

### Scalability Roadmap

1. **Phase 1**: Current architecture (1M students)
2. **Phase 2**: Redis cluster + read replicas (10M students)
3. **Phase 3**: Microservices + sharding (100M+ students)

---

## References

- [API Documentation](api/README.md)
- [Services Documentation](services/README.md)
- [DocTypes Documentation](doctypes/README.md)
- [Development Guide](development/README.md)

---

**Last Updated**: 2026-01-20
**Version**: 1.0


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


# Memora API Documentation

Complete reference for all Memora API endpoints organized by domain modules.

## Table of Contents

- [Overview](#overview)
- [Authentication](#authentication)
- [Base URL](#base-url)
- [Response Format](#response-format)
- [API Modules](#api-modules)
  - [Subjects & Tracks](#subjects--tracks)
  - [Map Engine](#map-engine)
  - [Sessions](#sessions)
  - [Reviews (SRS)](#reviews-srs)
  - [Profile](#profile)
  - [Quests](#quests)
  - [Leaderboard](#leaderboard)
  - [Onboarding](#onboarding)
  - [Store](#store)
  - [SRS Admin](#srs-admin)
- [Error Handling](#error-handling)
- [Rate Limiting](#rate-limiting)

## Overview

The Memora API is organized into domain-specific modules for better maintainability. All endpoints are whitelisted using Frappe's `@frappe.whitelist()` decorator and can be called from client-side applications.

### API Architecture

```
Client Application
        │
        ▼
┌─────────────────────┐
│  API Gateway        │  (api/__init__.py)
│  (Re-exports)      │
└──────────┬──────────┘
           │
    ┌──────┼──────┬─────────┬────────┐
    │      │      │         │        │
    ▼      ▼      ▼         ▼        ▼
Subjects Map  Sessions  Reviews  Profile  ...
```

## Authentication

All API endpoints require authentication through Frappe's session system:

- **Session-based**: User must be logged in via Frappe login
- **Token-based**: API keys can be used for programmatic access
- **Whitelisted**: All endpoints are protected by `@frappe.whitelist()` decorator

### Authentication Headers

```http
Cookie: sid=<session_id>
Authorization: token <api_key>:<api_secret>
```

## Base URL

```
https://your-domain.com/api/method/memora.api.<module>.<function>
```

### Example

```http
GET /api/method/memora.api.subjects.get_subjects
```

## Response Format

### Success Response

```json
{
  "message": {
    "data": {...},
    "status": "success"
  }
}
```

### Error Response

```json
{
  "exc": "Error message",
  "exc_type": "ValidationError",
  "_server_messages": "[\"Error details\"]"
}
```

## API Modules

### Subjects & Tracks

Module: [`memora/api/subjects.py`](../../memora/api/subjects.py)

#### `get_subjects()`

Get subjects based on user's academic plan with Arabic display names.

**Endpoint**: `GET /api/method/memora.api.subjects.get_subjects`

**Authentication**: Required

**Response**:
```json
{
  "message": [
    {
      "name": "mathematics",
      "title": "رياضيات",
      "icon": "📐",
      "is_paid": false
    }
  ]
}
```

**Logic**:
1. Fetch user's grade, stream, and academic year from Player Profile
2. Find matching Academic Plan
3. Return subjects with display names from plan
4. Returns empty list if onboarding not completed

---

#### `get_my_subjects()`

Get subjects specific to current user's Academic Plan with metadata.

**Endpoint**: `GET /api/method/memora.api.subjects.get_my_subjects`

**Authentication**: Required

**Response**:
```json
{
  "message": [
    {
      "id": "mathematics",
      "name": "رياضيات",
      "icon": "📐",
      "display_name": "رياضيات",
      "is_mandatory": true
    }
  ]
}
```

---

#### `get_game_tracks(subject)`

Get learning tracks for a given subject.

**Endpoint**: `GET /api/method/memora.api.subjects.get_game_tracks`

**Parameters**:
- `subject` (string, required): Subject name/ID

**Authentication**: Required

**Response**:
```json
{
  "message": [
    {
      "name": "track-1",
      "track_name": "Basic Track",
      "is_default": true,
      "unlock_level": 1,
      "icon": "🎯",
      "description": "Track description"
    }
  ]
}
```

---

### Map Engine

Module: [`memora/api/map_engine.py`](../../memora/api/map_engine.py)

#### `get_map_data(subject, track)`

Get learning map data for a subject and track.

**Endpoint**: `GET /api/method/memora.api.map_engine.get_map_data`

**Parameters**:
- `subject` (string, required): Subject name
- `track` (string, required): Track name

**Authentication**: Required

**Response**:
```json
{
  "message": {
    "units": [
      {
        "name": "unit-1",
        "title": "Algebra",
        "topics": [...]
      }
    ]
  }
}
```

---

#### `get_track_details(track)`

Get detailed information about a learning track.

**Endpoint**: `GET /api/method/memora.api.map_engine.get_track_details`

**Parameters**:
- `track` (string, required): Track name

**Authentication**: Required

---

#### `get_topic_details(topic_id)`

Get detailed information about a topic.

**Endpoint**: `GET /api/method/memora.api.map_engine.get_topic_details`

**Parameters**:
- `topic_id` (string, required): Topic ID

**Authentication**: Required

---

#### `get_unit_topics(unit_id)`

Get topics within a unit.

**Endpoint**: `GET /api/method/memora.api.map_engine.get_unit_topics`

**Parameters**:
- `unit_id` (string, required): Unit ID

**Authentication**: Required

---

### Sessions

Module: [`memora/api/sessions.py`](../../memora/api/sessions.py)

#### `get_lesson_details(lesson_id)`

Get lesson content with stages configuration.

**Endpoint**: `GET /api/method/memora.api.sessions.get_lesson_details`

**Parameters**:
- `lesson_id` (string, required): Lesson ID

**Authentication**: Required

**Response**:
```json
{
  "message": {
    "name": "lesson-1",
    "title": "Linear Equations",
    "xp_reward": 100,
    "stages": [
      {
        "id": "stage-1",
        "title": "Introduction",
        "type": "video",
        "config": {...}
      }
    ]
  }
}
```

**Error**: Returns error if lesson not found or not published

---

#### `submit_session(session_meta, gamification_results, interactions)`

Submit gameplay session with XP, score, and SRS tracking.

**Endpoint**: `POST /api/method/memora.api.sessions.submit_session`

**Parameters**:
- `session_meta` (object, required): Session metadata
  - `lesson_id` (string): Lesson ID
- `gamification_results` (object, required): Results data
  - `xp_earned` (number): XP earned
  - `score` (number): Score achieved
- `interactions` (array, required): Question interactions
  - Each interaction includes question ID, answer, correctness

**Authentication**: Required

**Response**:
```json
{
  "message": {
    "status": "success",
    "message": "Session Saved ✅"
  }
}
```

**Process**:
1. Archives gameplay session
2. Updates global XP
3. Updates subject progression (leaderboard)
4. Updates SRS memory tracking
5. All in single database transaction

---

### Reviews (SRS)

Module: [`memora/api/reviews.py`](../../memora/api/reviews.py)

#### `get_review_session(subject=None, topic_id=None)`

Get due questions for review session with Redis caching.

**Endpoint**: `GET /api/method/memora.api.reviews.get_review_session`

**Parameters**:
- `subject` (string, optional): Filter by subject
- `topic_id` (string, optional): Filter by topic

**Authentication**: Required

**Performance**: <100ms via Redis cache

**Response**:
```json
{
  "message": {
    "questions": [
      {
        "id": "q-1",
        "question_text": "...",
        "options": [...],
        "srs_data": {...}
      }
    ],
    "is_degraded": false,
    "season": "2024-2025"
  }
}
```

**Features**:
- Redis cache for instant retrieval
- Safe Mode fallback with rate limiting
- Lazy loading on cache miss
- Subject and topic filtering

---

#### `submit_review_session(session_data)`

Submit review session with async persistence.

**Endpoint**: `POST /api/method/memora.api.reviews.submit_review_session`

**Parameters**:
- `session_data` (object, required): Review session data
  - `questions` (array): Question answers
  - `subject` (string): Subject
  - `topic_id` (string): Topic ID

**Authentication**: Required

**Performance**: <500ms confirmation

**Response**:
```json
{
  "message": {
    "xp_earned": 120,
    "remaining_items": 45,
    "persistence_job_id": "job_12345"
  }
}
```

**Process**:
1. Synchronous Redis update
2. Asynchronous database persistence
3. Returns job ID for tracking
4. Audit logging

---

### Profile

Module: [`memora/api/profile.py`](../../memora/api/profile.py)

#### `get_player_profile()`

Get basic player profile data on app load.

**Endpoint**: `GET /api/method/memora.api.profile.get_player_profile`

**Authentication**: Required

**Response**:
```json
{
  "message": {
    "xp": 1500,
    "gems": 50,
    "current_grade": "Grade 10",
    "current_stream": "Science"
  }
}
```

---

#### `get_full_profile_stats(subject=None)`

Get comprehensive profile statistics with level, streak, and mastery.

**Endpoint**: `GET /api/method/memora.api.profile.get_full_profile_stats`

**Parameters**:
- `subject` (string, optional): Filter by subject

**Authentication**: Required

**Response**:
```json
{
  "message": {
    "fullName": "John Doe",
    "avatarUrl": "/files/avatar.jpg",
    "level": 5,
    "levelTitle": "حارس الذاكرة",
    "nextLevelProgress": 65,
    "xpInLevel": 350,
    "xpToNextLevel": 500,
    "streak": 7,
    "gems": 0,
    "totalXP": 1500,
    "totalLearned": 250,
    "weeklyActivity": [
      {
        "day": "سبت",
        "full_date": "2026-01-20",
        "xp": 120,
        "isToday": true
      }
    ],
    "mastery": {
      "new": 50,
      "learning": 100,
      "mature": 100
    }
  }
}
```

**Calculations**:
- **Level**: `int(0.07 * sqrt(xp)) + 1`
- **Streak**: Consecutive days of activity
- **Mastery**: Based on SRS stability levels

---

### Quests

Module: [`memora/api/quests.py`](../../memora/api/quests.py)

#### `get_daily_quests()`

Get daily quests for the current user.

**Endpoint**: `GET /api/method/memora.api.quests.get_daily_quests`

**Authentication**: Required

**Response**:
```json
{
  "message": [
    {
      "id": "quest-1",
      "title": "Complete 3 Lessons",
      "description": "Complete 3 lessons today",
      "xp_reward": 50,
      "progress": 1,
      "target": 3,
      "completed": false
    }
  ]
}
```

---

### Leaderboard

Module: [`memora/api/leaderboard.py`](../../memora/api/leaderboard.py)

#### `get_leaderboard(subject=None, period="weekly")`

Get leaderboard rankings.

**Endpoint**: `GET /api/method/memora.api.leaderboard.get_leaderboard`

**Parameters**:
- `subject` (string, optional): Filter by subject
- `period` (string, optional): Time period (daily, weekly, monthly, all-time)

**Authentication**: Required

**Response**:
```json
{
  "message": {
    "rankings": [
      {
        "rank": 1,
        "player": "John Doe",
        "xp": 2500,
        "level": 8,
        "avatar": "/files/avatar1.jpg"
      }
    ],
    "current_user_rank": 5
  }
}
```

---

### Onboarding

Module: [`memora/api/onboarding.py`](../../memora/api/onboarding.py)

#### `get_academic_masters()`

Get available academic grades, streams, and plans.

**Endpoint**: `GET /api/method/memora.api.onboarding.get_academic_masters`

**Authentication**: Required

**Response**:
```json
{
  "message": {
    "grades": ["Grade 9", "Grade 10", "Grade 11"],
    "streams": ["Science", "Arts", "Commerce"],
    "plans": ["CBSE", "ICSE", "State Board"]
  }
}
```

---

#### `set_academic_profile(grade, stream, academic_year)`

Set user's academic profile during onboarding.

**Endpoint**: `POST /api/method/memora.api.onboarding.set_academic_profile`

**Parameters**:
- `grade` (string, required): Academic grade
- `stream` (string, optional): Academic stream
- `academic_year` (string, required): Academic year

**Authentication**: Required

**Response**:
```json
{
  "message": {
    "status": "success",
    "profile_updated": true
  }
}
```

---

### Store

Module: [`memora/api/store.py`](../../memora/api/store.py)

#### `get_store_items()`

Get available items in the in-app store.

**Endpoint**: `GET /api/method/memora.api.store.get_store_items`

**Authentication**: Required

**Response**:
```json
{
  "message": [
    {
      "id": "item-1",
      "name": "Premium Subscription",
      "description": "Full access to all content",
      "price": 9.99,
      "currency": "USD",
      "type": "subscription"
    }
  ]
}
```

---

#### `request_purchase(item_id, payment_method)`

Request purchase of an item.

**Endpoint**: `POST /api/method/memora.api.store.request_purchase`

**Parameters**:
- `item_id` (string, required): Item ID
- `payment_method` (string, required): Payment method

**Authentication**: Required

**Response**:
```json
{
  "message": {
    "status": "success",
    "purchase_id": "purchase-123",
    "redirect_url": "https://payment-gateway.com/..."
  }
}
```

---

### SRS Admin

Module: [`memora/api/srs.py`](../../memora/api/srs.py)

#### `get_cache_status()`

Monitor Redis cache health and statistics.

**Endpoint**: `GET /api/method/memora.api.srs.get_cache_status`

**Authentication**: Required (System Manager role)

**Response**:
```json
{
  "message": {
    "redis_connected": true,
    "is_safe_mode": false,
    "memory_used_mb": 245.67,
    "total_keys": 125000,
    "keys_by_season": {
      "2024-2025": 85000,
      "2023-2024": 40000
    }
  }
}
```

---

#### `rebuild_season_cache(season_name)`

Trigger full cache rebuild for a season.

**Endpoint**: `POST /api/method/memora.api.srs.rebuild_season_cache`

**Parameters**:
- `season_name` (string, required): Season name (e.g., "2024-2025")

**Authentication**: Required (System Manager role)

**Response**:
```json
{
  "message": {
    "status": "started",
    "job_id": "cache_rebuild_2024-2025_2024-01-20",
    "estimated_records": 85000
  }
}
```

---

#### `archive_season(season_name, confirm=False)`

Archive season data to cold storage.

**Endpoint**: `POST /api/method/memora.api.srs.archive_season`

**Parameters**:
- `season_name` (string, required): Season name
- `confirm` (boolean, required): Must be true to confirm

**Authentication**: Required (System Manager role)

**Response**:
```json
{
  "message": {
    "success": true,
    "archived_count": 45000,
    "message": "Season archived successfully"
  }
}
```

---

#### `get_archive_status(season_name)`

Get archive status for a season.

**Endpoint**: `GET /api/method/memora.api.srs.get_archive_status`

**Parameters**:
- `season_name` (string, required): Season name

**Authentication**: Required

**Response**:
```json
{
  "message": {
    "active_records": 0,
    "archived_records": 45000,
    "eligible_for_deletion": 12000,
    "archived_at": "2024-01-15T10:30:00"
  }
}
```

---

#### `delete_eligible_archived_records(season_name=None, confirm=False)`

Delete archived records marked for deletion.

**Endpoint**: `POST /api/method/memora.api.srs.delete_eligible_archived_records`

**Parameters**:
- `season_name` (string, optional): Filter by season
- `confirm` (boolean, required): Must be true to confirm

**Authentication**: Required (System Manager role)

**Response**:
```json
{
  "message": {
    "success": true,
    "deleted_count": 12000,
    "message": "Deleted 12,000 eligible records"
  }
}
```

---

#### `trigger_reconciliation()`

Manually trigger cache reconciliation.

**Endpoint**: `POST /api/method/memora.api.srs.trigger_reconciliation`

**Authentication**: Required (System Manager role)

**Response**:
```json
{
  "message": {
    "status": "started",
    "job_id": "reconciliation_2024-01-20"
  }
}
```

---

## Error Handling

### Common Error Codes

| Error Code | Description | HTTP Status |
|------------|-------------|-------------|
| `ValidationError` | Invalid input data | 400 |
| `PermissionError` | Insufficient permissions | 403 |
| `NotFoundError` | Resource not found | 404 |
| `RateLimitError` | Too many requests | 429 |
| `ServerError` | Internal server error | 500 |

### Error Response Format

```json
{
  "exc": "Validation Error: Lesson ID is missing",
  "exc_type": "ValidationError",
  "_server_messages": "[\"Validation Error: Lesson ID is missing\"]"
}
```

## Rate Limiting

### Safe Mode Rate Limits

When Redis is unavailable, the system enters Safe Mode with rate limiting:

- **Global Limit**: 500 requests per minute
- **Per-User Limit**: 1 request per 30 seconds
- **Result Limit**: Maximum 15 items per request

### Rate Limit Response

```json
{
  "message": "Rate limit exceeded. Please try again later."
}
```

---

## API Versioning

Current API version: **v1**

All endpoints are version-agnostic. Breaking changes will be announced in advance.

## Best Practices

1. **Always handle errors**: Check for error responses and handle gracefully
2. **Use caching**: Leverage Redis caching for SRS operations
3. **Batch requests**: Minimize API calls by batching related operations
4. **Monitor rate limits**: Respect rate limits, especially in Safe Mode
5. **Validate inputs**: Always validate data before sending to API
6. **Handle async operations**: For `submit_review_session`, track persistence job if needed

## Testing

### Example cURL Commands

```bash
# Get subjects
curl -X GET "https://your-domain.com/api/method/memora.api.subjects.get_subjects" \
  -H "Cookie: sid=<session_id>"

# Submit session
curl -X POST "https://your-domain.com/api/method/memora.api.sessions.submit_session" \
  -H "Cookie: sid=<session_id>" \
  -H "Content-Type: application/json" \
  -d '{
    "session_meta": {"lesson_id": "lesson-1"},
    "gamification_results": {"xp_earned": 100, "score": 85},
    "interactions": [...]
  }'
```

---

**Last Updated**: 2026-01-20
**API Version**: 1.0


# Memora Development Guide

Complete guide for setting up and developing the Memora application.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Development Setup](#development-setup)
- [Project Structure](#project-structure)
- [Development Workflow](#development-workflow)
- [Code Style Guidelines](#code-style-guidelines)
- [Testing](#testing)
- [Debugging](#debugging)
- [Deployment](#deployment)
- [Troubleshooting](#troubleshooting)

## Prerequisites

### System Requirements

- **Operating System**: Linux, macOS, or Windows with WSL
- **Python**: 3.11 or higher
- **Node.js**: 16.x or higher (for frontend tools)
- **PostgreSQL**: 14.x or higher
- **Redis**: 6.x or higher
- **Git**: Latest version

### Software Requirements

- **Bench**: Frappe bench CLI tool
- **Frappe Framework**: v15 or higher
- **Python Packages**: See `pyproject.toml`
- **Node Packages**: See `package.json` (if applicable)

### Hardware Requirements

- **RAM**: Minimum 4GB, Recommended 8GB+
- **Disk Space**: Minimum 20GB free space
- **CPU**: 2+ cores recommended

## Installation

### Step 1: Install Bench

```bash
# Clone bench repository
git clone https://github.com/frappe/bench ~/bench-repo

# Install bench
cd ~/bench-repo
sudo python3 install.py --user

# Add to PATH (add to ~/.bashrc or ~/.zshrc)
export PATH=$PATH:~/.local/bin
```

### Step 2: Create New Bench

```bash
# Create a new bench
bench init my-bench --frappe-branch version-15

cd my-bench
```

### Step 3: Install Memora

```bash
# Get the app
bench get-app https://github.com/your-org/memora --branch develop

# Install the app
bench install-app memora
```

### Step 4: Configure Redis

Edit `sites/common_site_config.json`:

```json
{
  "redis_cache": "redis://localhost:13000",
  "srs_redis_cache": "redis://localhost:13000"
}
```

### Step 5: Start Services

```bash
# Start Redis
redis-server --port 13000

# Start Frappe development server
bench start
```

## Development Setup

### Initial Setup

```bash
# Navigate to bench directory
cd ~/my-bench

# Switch to development site
bench use site1.local

# Enable developer mode
bench set-config developer_mode 1

# Clear cache
bench clear-cache
```

### Pre-commit Hooks

Install pre-commit hooks for code quality:

```bash
cd apps/memora
pre-commit install
```

Pre-commit tools configured:
- **ruff**: Python linting and formatting
- **eslint**: JavaScript linting
- **prettier**: Code formatting
- **pyupgrade**: Python syntax modernization

### Database Setup

```bash
# Create database (if not exists)
bench new-site site1.local --db-root-user root --db-root-password yourpassword

# Install memora on site
bench --site site1.local install-app memora

# Run migrations
bench --site site1.local migrate
```

### Running Benchmarks

```bash
# Run performance tests
cd apps/memora
pytest memora/tests/performance_test.py
```

## Project Structure

```
memora/
├── api/                    # API endpoints (modular)
│   ├── __init__.py        # Public API gateway
│   ├── utils.py           # Shared utilities
│   ├── subjects.py        # Subjects & tracks
│   ├── map_engine.py      # Learning map
│   ├── sessions.py        # Gameplay sessions
│   ├── reviews.py         # Review sessions (SRS)
│   ├── srs.py            # SRS admin endpoints
│   ├── profile.py         # Player profiles
│   ├── quests.py          # Daily quests
│   ├── leaderboard.py     # Leaderboards
│   ├── onboarding.py      # User onboarding
│   └── store.py         # In-app store
├── services/              # Business logic services
│   ├── srs_redis_manager.py      # Redis operations
│   ├── srs_persistence.py        # Async DB writes
│   ├── srs_archiver.py           # Season archival
│   ├── srs_reconciliation.py     # Cache consistency
│   └── partition_manager.py      # DB partitioning
├── memora/doctype/         # Frappe DocTypes
│   ├── player_profile/
│   ├── player_memory_tracker/
│   ├── gameplay_session/
│   ├── game_subject/
│   ├── game_topic/
│   ├── game_lesson/
│   └── ...
├── patches/                # Database migrations
│   └── v1_0/
│       ├── setup_partitioning.py
│       └── fix_null_seasons.py
├── tests/                  # Test suite
│   ├── test_srs_archiver.py
│   ├── test_srs_redis.py
│   ├── test_srs_reconciliation.py
│   └── performance_test.py
├── public/                 # Static assets
│   ├── js/
│   ├── css/
│   └── images/
├── templates/              # Jinja templates
├── config/                # Configuration files
├── setup_folder/          # Setup scripts
│   └── infrastructure.py
├── hooks.py              # Frappe hooks
├── setup.py              # Python package setup
├── pyproject.toml       # Python dependencies
└── README.md            # App documentation
```

## Development Workflow

### Creating a New Feature

1. **Create Feature Branch**
   ```bash
   bench switch-to-branch feature/my-new-feature
   ```

2. **Make Changes**
   - Edit files in appropriate modules
   - Follow code style guidelines
   - Write tests for new functionality

3. **Run Tests**
   ```bash
   # Run all tests
   bench --site site1.local run-tests --app memora

   # Run specific test file
   cd apps/memora
   pytest memora/tests/test_srs_archiver.py
   ```

4. **Run Pre-commit**
   ```bash
   cd apps/memora
   pre-commit run --all-files
   ```

5. **Commit Changes**
   ```bash
   git add .
   git commit -m "feat: add new feature"
   ```

6. **Push and Create PR**
   ```bash
   git push origin feature/my-new-feature
   ```

### Adding New API Endpoint

1. **Choose Module**: Select appropriate API module (e.g., `subjects.py`)

2. **Add Function**:
   ```python
   @frappe.whitelist()
   def my_new_endpoint(param1, param2):
       """My new endpoint documentation"""
       try:
           # Your logic here
           return {"status": "success", "data": result}
       except Exception as e:
           frappe.log_error(str(e), "my_new_endpoint")
           frappe.throw(str(e))
   ```

3. **Export in `__init__.py`**:
   ```python
   from .my_module import my_new_endpoint
   ```

4. **Write Tests**: Create test file in `tests/`

5. **Update Documentation**: Update API documentation

### Adding New DocType

1. **Create DocType Directory**:
   ```bash
   bench --site site1.local make-doctype "My New DocType" memora
   ```

2. **Define Fields**: Edit JSON file

3. **Add Controller Logic**: Edit Python file

4. **Create Tests**: Create test file

5. **Run Migration**:
   ```bash
   bench --site site1.local migrate
   ```

### Adding New Service

1. **Create Service File**:
   ```python
   # memora/services/my_service.py
   class MyService:
       def __init__(self):
           pass
       
       def my_method(self, param):
           # Logic here
           pass
   ```

2. **Use Service**:
   ```python
   from memora.services.my_service import MyService
   
   service = MyService()
   result = service.my_method(param)
   ```

3. **Write Tests**: Create test file

## Code Style Guidelines

### Python Code Style

Follow PEP 8 conventions:

```python
# Good
def calculate_xp(score: int, difficulty: float) -> int:
    """Calculate XP based on score and difficulty."""
    return int(score * difficulty)

# Bad
def CalculateXP(s,d):
    return s*d
```

### Type Hints

Use type hints for function signatures:

```python
from typing import List, Dict, Optional

def get_user_data(user_id: str) -> Optional[Dict]:
    """Get user data by ID."""
    pass

def process_items(items: List[str]) -> Dict[str, int]:
    """Process list of items."""
    pass
```

### Docstrings

Use Google-style docstrings:

```python
def get_review_session(user: str, season: str) -> Dict:
    """Get review session for a user.
    
    Args:
        user: User email or ID
        season: Season name
        
    Returns:
        Dictionary with review session data
        
    Raises:
        ValidationError: If user not found
    """
    pass
```

### Error Handling

Always handle errors gracefully:

```python
try:
    result = operation()
except SpecificError as e:
    frappe.log_error(str(e), "function_name")
    frappe.throw(_("Operation failed"))
except Exception as e:
    frappe.log_error(frappe.get_traceback(), "function_name")
    frappe.throw(_("An unexpected error occurred"))
```

### Database Queries

Use Frappe's database API:

```python
# Good: Use Frappe API
records = frappe.get_all(
    "Player Memory Tracker",
    filters={"player": user, "season": season},
    fields=["question_id", "stability"],
    limit=20
)

# Acceptable: Raw SQL for complex queries
records = frappe.db.sql("""
    SELECT question_id, stability
    FROM `tabPlayer Memory Tracker`
    WHERE player = %s AND season = %s
    LIMIT 20
""", (user, season), as_dict=True)
```

### API Endpoints

Always use `@frappe.whitelist()` decorator:

```python
@frappe.whitelist()
def my_endpoint(param: str) -> Dict:
    """My endpoint."""
    pass
```

## Testing

### Running Tests

```bash
# Run all tests
bench --site site1.local run-tests --app memora

# Run specific test file
cd apps/memora
pytest memora/tests/test_srs_archiver.py -v

# Run with coverage
pytest --cov=memora memora/tests/ --cov-report=html
```

### Writing Tests

```python
import frappe
from frappe.tests.utils import FrappeTestCase
import pytest

class TestMyService(FrappeTestCase):
    def setUp(self):
        """Setup before each test."""
        frappe.set_user("Administrator")
    
    def tearDown(self):
        """Cleanup after each test."""
        frappe.db.rollback()
    
    def test_my_function(self):
        """Test my function."""
        result = my_function(param="test")
        self.assertEqual(result, expected_value)
```

### Test Coverage

Aim for 80%+ test coverage:

```bash
# Generate coverage report
pytest --cov=memora memora/tests/ --cov-report=term-missing
```

## Debugging

### Enable Debug Mode

```bash
bench set-config developer_mode 1
bench set-config logging_level DEBUG
```

### View Logs

```bash
# View Frappe logs
bench --site site1.local tail-logs

# View Redis logs
tail -f /var/log/redis/redis.log
```

### Use Python Debugger

```python
import pdb; pdb.set_trace()

# Or use ipdb if installed
import ipdb; ipdb.set_trace()
```

### Debug API Endpoints

```python
@frappe.whitelist()
def my_endpoint():
    """Debug endpoint."""
    import frappe
    frappe.logger().debug("Debug message")
    # Your logic
    pass
```

## Deployment

### Production Setup

1. **Disable Developer Mode**
   ```bash
   bench set-config developer_mode 0
   ```

2. **Set Production Configuration**
   ```json
   {
     "redis_cache": "redis://redis-server:6379",
     "srs_redis_cache": "redis://redis-server:6379",
     "maintenance_mode": 0
   }
   ```

3. **Run Migrations**
   ```bash
   bench --site site1.local migrate
   ```

4. **Build Assets**
   ```bash
   bench build --app memora
   ```

5. **Restart Services**
   ```bash
   bench restart
   ```

### Monitoring

Monitor key metrics:
- **Redis**: Memory usage, connection count
- **PostgreSQL**: Query performance, connection pool
- **Application**: Response times, error rates

## Troubleshooting

### Common Issues

#### Redis Connection Failed

**Problem**: Cannot connect to Redis

**Solution**:
```bash
# Check if Redis is running
redis-cli -p 13000 ping

# Start Redis
redis-server --port 13000

# Check configuration
cat sites/common_site_config.json
```

#### Database Migration Failed

**Problem**: Migration fails with error

**Solution**:
```bash
# Check migration status
bench --site site1.local migrate --skip-failing

# Manually fix migration
# Edit migration file and re-run
bench --site site1.local migrate
```

#### Tests Failing

**Problem**: Tests fail intermittently

**Solution**:
```bash
# Clear cache
bench clear-cache

# Rebuild database
bench --site site1.local reinstall-app memora

# Run tests with verbose output
pytest -v memora/tests/
```

#### Performance Issues

**Problem**: Slow API responses

**Solution**:
```bash
# Check Redis cache status
frappe.get_doc("Memora Settings").get_cache_status()

# Rebuild cache if needed
from memora.services.srs_redis_manager import rebuild_season_cache
rebuild_season_cache("2024-2025")

# Check database indexes
# Use EXPLAIN ANALYZE on slow queries
```

### Getting Help

- **Documentation**: Check `/docs` folder
- **Logs**: Review error logs
- **Community**: Ask in Frappe community
- **Support**: Email dev@corex.com

---

## Additional Resources

- [Frappe Framework Docs](https://frappeframework.com/docs)
- [Python Documentation](https://docs.python.org/3/)
- [Redis Documentation](https://redis.io/documentation)
- [PostgreSQL Documentation](https://www.postgresql.org/docs/)

---

**Last Updated**: 2026-01-20
**Version**: 1.0


# Memora DocTypes Documentation

Complete reference for all Memora data models (DocTypes) in the Frappe framework.

## Table of Contents

- [Overview](#overview)
- [DocType Categories](#doctype-categories)
- [Core DocTypes](#core-doctypes)
  - [Player Profile](#player-profile)
  - [Player Memory Tracker](#player-memory-tracker)
  - [Gameplay Session](#gameplay-session)
- [Content DocTypes](#content-doctypes)
  - [Game Subject](#game-subject)
  - [Game Topic](#game-topic)
  - [Game Lesson](#game-lesson)
  - [Game Stage](#game-stage)
- [Academic Structure DocTypes](#academic-structure-doctypes)
  - [Game Academic Grade](#game-academic-grade)
  - [Game Academic Stream](#game-academic-stream)
  - [Game Academic Plan](#game-academic-plan)
  - [Game Learning Track](#game-learning-track)
  - [Game Unit](#game-unit)
- [Subscription DocTypes](#subscription-doctypes)
  - [Game Subscription Season](#game-subscription-season)
  - [Game Subscription Access](#game-subscription-access)
  - [Game Player Subscription](#game-player-subscription)
  - [Game Purchase Request](#game-purchase-request)
  - [Game Sales Item](#game-sales-item)
- [Gamification DocTypes](#gamification-doctypes)
  - [Player Subject Score](#player-subject-score)
  - [Game Daily Quest](#game-daily-quest)
- [System DocTypes](#system-doctypes)
  - [Archived Memory Tracker](#archived-memory-tracker)
  - [Game Player Device](#game-player-device)
- [DocType Relationships](#doctype-relationships)

## Overview

Memora uses Frappe's DocType system to define data models. Each DocType represents a database table with fields, permissions, and business logic.

### DocType Structure

```json
{
  "name": "DocType Name",
  "module": "Memora",
  "fields": [...],
  "permissions": [...],
  "indexes": [...]
}
```

### File Structure

```
memora/memora/doctype/
├── player_profile/
│   ├── player_profile.json    # Schema definition
│   ├── player_profile.py      # Controller logic
│   └── test_player_profile.py # Tests
├── player_memory_tracker/
├── gameplay_session/
└── ...
```

## DocType Categories

### 1. Core DocTypes
Essential data models for player management and gameplay tracking.

### 2. Content DocTypes
Educational content structure (subjects, topics, lessons).

### 3. Academic Structure DocTypes
Academic hierarchy (grades, streams, plans, tracks).

### 4. Subscription DocTypes
Subscription and purchase management.

### 5. Gamification DocTypes
XP, scores, quests, and leaderboards.

### 6. System DocTypes
System-level data and archival.

## Core DocTypes

### Player Profile

**Module**: [`memora/memora/doctype/player_profile/`](../../memora/memora/doctype/player_profile/)

**Purpose**: Stores player profile information including XP, gems, and academic details.

**Naming**: `PROFILE-{user}` (auto-generated)

#### Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `user` | Link (User) | Yes | Linked Frappe User account |
| `total_xp` | Int | No | Total experience points earned |
| `gems_balance` | Int | No | Gems balance (deprecated) |
| `current_grade` | Link (Game Academic Grade) | No | Current academic grade |
| `current_stream` | Link (Game Academic Stream) | No | Current academic stream |
| `academic_year` | Data | No | Current academic year |
| `devices` | Table (Game Player Device) | No | Registered devices |

#### Permissions

- **System Manager**: Full access (create, read, write, delete, share, export, print, email, report)

#### Usage

```python
# Get player profile
profile = frappe.get_doc("Player Profile", {"user": user})

# Update XP
profile.total_xp += 100
profile.save()
```

---

### Player Memory Tracker

**Module**: [`memora/memora/doctype/player_memory_tracker/`](../../memora/memora/doctype/player_memory_tracker/)

**Purpose**: Tracks SRS (Spaced Repetition System) data for each question-player interaction.

**Naming**: Random hash (auto-generated)

**Partitioning**: LIST COLUMNS by `season` for performance

#### Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `player` | Link (User) | Yes | Player who interacted with question |
| `question_id` | Data | Yes | Unique question identifier |
| `subject` | Link (Game Subject) | No | Subject the question belongs to |
| `topic` | Link (Game Topic) | No | Topic the question belongs to |
| `stability` | Float | No | SRS stability level (0.0-4.0) |
| `next_review_date` | Datetime | No | When question should be reviewed next |
| `last_review_date` | Datetime | No | Last time question was reviewed |
| `season` | Link (Game Subscription Season) | Yes | Season for partitioning |

#### Stability Levels

| Level | Name | Description |
|-------|------|-------------|
| 0.0 - 1.0 | New | Recently introduced question |
| 1.0 - 2.0 | Learning | In learning phase |
| 2.0 - 3.0 | Review | Regular review needed |
| 3.0 - 4.0 | Mature | Well-learned, infrequent reviews |
| 4.0+ | Mastered | Fully mastered |

#### Permissions

- **System Manager**: Full access

#### Usage

```python
# Create memory tracker
tracker = frappe.get_doc({
    "doctype": "Player Memory Tracker",
    "player": user,
    "question_id": "q-123",
    "subject": "mathematics",
    "topic": "algebra",
    "stability": 1.0,
    "next_review_date": frappe.utils.add_days(frappe.utils.now(), 1),
    "season": "2024-2025"
})
tracker.insert()
```

---

### Gameplay Session

**Module**: [`memora/memora/doctype/gameplay_session/`](../../memora/memora/doctype/gameplay_session/)

**Purpose**: Archives gameplay session data including interactions, XP earned, and scores.

**Naming**: Random hash (auto-generated)

#### Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `player` | Link (User) | Yes | Player who completed the session |
| `lesson` | Link (Game Lesson) | Yes | Lesson completed |
| `raw_data` | Code (JSON) | No | Full interaction data |
| `xp_earned` | Int | No | XP earned in this session |
| `score` | Int | No | Score achieved in this session |

#### Permissions

- **System Manager**: Full access

#### Usage

```python
# Create gameplay session
session = frappe.get_doc({
    "doctype": "Gameplay Session",
    "player": user,
    "lesson": "lesson-123",
    "raw_data": json.dumps(interactions),
    "xp_earned": 100,
    "score": 85
})
session.insert()
```

---

## Content DocTypes

### Game Subject

**Module**: [`memora/memora/doctype/game_subject/`](../../memora/memora/doctype/game_subject/)

**Purpose**: Defines educational subjects (e.g., Mathematics, Science).

**Naming**: Based on `title` field

#### Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `title` | Data | Yes | Subject name (unique) |
| `icon` | Attach Image | No | Subject icon/image |
| `is_published` | Check | No | Whether subject is published |
| `is_paid` | Check | No | Whether subject requires subscription |
| `full_price` | Currency | No | Full price |
| `discounted_price` | Currency | No | Discounted price |

#### Permissions

- **System Manager**: Full access

---

### Game Topic

**Module**: [`memora/memora/doctype/game_topic/`](../../memora/memora/doctype/game_topic/)

**Purpose**: Defines topics within subjects (e.g., Algebra within Mathematics).

**Naming**: Based on `title` field

#### Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `title` | Data | Yes | Topic name |
| `subject` | Link (Game Subject) | Yes | Parent subject |
| `description` | Text | No | Topic description |
| `is_published` | Check | No | Whether topic is published |

---

### Game Lesson

**Module**: [`memora/memora/doctype/game_lesson/`](../../memora/memora/doctype/game_lesson/)

**Purpose**: Defines lessons with multiple stages (videos, quizzes, etc.).

**Naming**: Auto-generated

#### Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `title` | Data | Yes | Lesson title |
| `subject` | Link (Game Subject) | Yes | Parent subject |
| `topic` | Link (Game Topic) | Yes | Parent topic |
| `unit` | Link (Game Unit) | Yes | Parent unit |
| `xp_reward` | Int | No | XP reward for completion |
| `stages` | Table (Game Stage) | No | Lesson stages |

#### Stages

Each lesson contains multiple stages with different types:
- **Video**: Video content
- **Quiz**: Quiz questions
- **Interactive**: Interactive exercises
- **Reading**: Reading material

---

### Game Stage

**Module**: [`memora/memora/doctype/game_stage/`](../../memora/memora/doctype/game_stage/)

**Purpose**: Defines individual stages within a lesson.

#### Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `title` | Data | Yes | Stage title |
| `type` | Select | Yes | Stage type (video, quiz, etc.) |
| `config` | Code (JSON) | No | Stage configuration |
| `order` | Int | No | Stage order within lesson |

---

## Academic Structure DocTypes

### Game Academic Grade

**Module**: [`memora/memora/doctype/game_academic_grade/`](../../memora/memora/doctype/game_academic_grade/)

**Purpose**: Defines academic grades (e.g., Grade 9, Grade 10).

**Naming**: Based on `grade_name` field

#### Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `grade_name` | Data | Yes | Grade name |
| `order` | Int | No | Display order |

---

### Game Academic Stream

**Module**: [`memora/memora/doctype/game_academic_stream/`](../../memora/memora/doctype/game_academic_stream/)

**Purpose**: Defines academic streams (e.g., Science, Arts, Commerce).

**Naming**: Based on `stream_name` field

#### Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `stream_name` | Data | Yes | Stream name |
| `order` | Int | No | Display order |

---

### Game Academic Plan

**Module**: [`memora/memora/doctype/game_academic_plan/`](../../memora/memora/doctype/game_academic_plan/)

**Purpose**: Defines academic plans for specific grade/stream/year combinations (e.g., CBSE Grade 10 Science).

**Naming**: Auto-generated

#### Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `grade` | Link (Game Academic Grade) | Yes | Academic grade |
| `stream` | Link (Game Academic Stream) | No | Academic stream |
| `year` | Data | Yes | Academic year |
| `subjects` | Table (Game Plan Subject) | Yes | Subjects in plan |

#### Game Plan Subject (Child Table)

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `subject` | Link (Game Subject) | Yes | Subject |
| `display_name` | Data | No | Custom display name |
| `is_mandatory` | Check | No | Whether subject is mandatory |

---

### Game Learning Track

**Module**: [`memora/memora/doctype/game_learning_track/`](../../memora/memora/doctype/game_learning_track/)

**Purpose**: Defines learning tracks within subjects (e.g., Basic Track, Advanced Track).

**Naming**: Auto-generated

#### Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `subject` | Link (Game Subject) | Yes | Parent subject |
| `track_name` | Data | Yes | Track name |
| `is_default` | Check | No | Whether this is the default track |
| `unlock_level` | Int | No | Level required to unlock |
| `icon` | Attach Image | No | Track icon |
| `description` | Text | No | Track description |

---

### Game Unit

**Module**: [`memora/memora/doctype/game_unit/`](../../memora/memora/doctype/game_unit/)

**Purpose**: Defines units within learning tracks (e.g., Unit 1: Linear Equations).

**Naming**: Auto-generated

#### Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `learning_track` | Link (Game Learning Track) | Yes | Parent track |
| `subject` | Link (Game Subject) | Yes | Subject |
| `topic` | Link (Game Topic) | Yes | Topic |
| `unit_name` | Data | Yes | Unit name |
| `order` | Int | No | Display order |

---

## Subscription DocTypes

### Game Subscription Season

**Module**: [`memora/memora/doctype/game_subscription_season/`](../../memora/memora/doctype/game_subscription_season/)

**Purpose**: Defines subscription seasons (e.g., "2024-2025").

**Naming**: Based on `season_name` field

#### Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `season_name` | Data | Yes | Season name |
| `start_date` | Date | Yes | Season start date |
| `end_date` | Date | Yes | Season end date |
| `is_active` | Check | No | Whether season is active |
| `auto_archive` | Check | No | Whether to auto-archive after season |

---

### Game Subscription Access

**Module**: [`memora/memora/doctype/game_subscription_access/`](../../memora/memora/doctype/game_subscription_access/)

**Purpose**: Controls access to content based on subscriptions.

#### Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `player` | Link (User) | Yes | Player |
| `season` | Link (Game Subscription Season) | Yes | Season |
| `subject` | Link (Game Subject) | No | Subject (if specific) |
| `access_type` | Select | Yes | Access type (full, limited, trial) |
| `expiry_date` | Date | No | Access expiry date |

---

### Game Player Subscription

**Module**: [`memora/memora/doctype/game_player_subscription/`](../../memora/memora/doctype/game_player_subscription/)

**Purpose**: Stores player subscription information.

#### Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `player` | Link (User) | Yes | Player |
| `season` | Link (Game Subscription Season) | Yes | Season |
| `subscription_type` | Select | Yes | Subscription type |
| `start_date` | Date | Yes | Start date |
| `end_date` | Date | Yes | End date |
| `is_active` | Check | No | Whether subscription is active |

---

### Game Purchase Request

**Module**: [`memora/memora/doctype/game_purchase_request/`](../../memora/memora/doctype/game_purchase_request/)

**Purpose**: Tracks in-app purchase requests.

#### Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `player` | Link (User) | Yes | Player |
| `item` | Link (Game Sales Item) | Yes | Item to purchase |
| `amount` | Currency | Yes | Purchase amount |
| `status` | Select | Yes | Purchase status |
| `payment_method` | Select | No | Payment method |
| `transaction_id` | Data | No | Transaction ID |

---

### Game Sales Item

**Module**: [`memora/memora/doctype/game_sales_item/`](../../memora/memora/doctype/game_sales_item/)

**Purpose**: Defines items available for purchase.

#### Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `item_name` | Data | Yes | Item name |
| `item_type` | Select | Yes | Item type (subscription, bundle, gems) |
| `price` | Currency | Yes | Item price |
| `currency` | Data | Yes | Currency code |
| `is_active` | Check | No | Whether item is available |

---

## Gamification DocTypes

### Player Subject Score

**Module**: [`memora/memora/doctype/player_subject_score/`](../../memora/memora/doctype/player_subject_score/)

**Purpose**: Tracks player scores and XP per subject.

#### Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `player` | Link (User) | Yes | Player |
| `subject` | Link (Game Subject) | Yes | Subject |
| `total_xp` | Int | No | Total XP in subject |
| `level` | Int | No | Current level in subject |
| `rank` | Int | No | Current rank |

---

### Game Daily Quest

**Module**: [`memora/memora/doctype/game_daily_quest/`](../../memora/memora/doctype/game_daily_quest/)

**Purpose**: Defines daily quests for players.

#### Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `quest_title` | Data | Yes | Quest title |
| `quest_type` | Select | Yes | Quest type |
| `target` | Int | Yes | Target value |
| `xp_reward` | Int | Yes | XP reward |
| `is_active` | Check | No | Whether quest is active |

---

## System DocTypes

### Archived Memory Tracker

**Module**: [`memora/memora/doctype/archived_memory_tracker/`](../../memora/memora/doctype/archived_memory_tracker/)

**Purpose**: Stores archived SRS data from old seasons.

**Naming**: Auto-generated

#### Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `player` | Link (User) | Yes | Player |
| `question_id` | Data | Yes | Question ID |
| `subject` | Link (Game Subject) | No | Subject |
| `topic` | Link (Game Topic) | No | Topic |
| `stability` | Float | No | Stability level |
| `next_review_date` | Datetime | No | Next review date |
| `last_review_date` | Datetime | No | Last review date |
| `season` | Link (Game Subscription Season) | Yes | Archived season |
| `archived_at` | Datetime | No | When record was archived |
| `eligible_for_deletion` | Check | No | Whether record can be deleted |

---

### Game Player Device

**Module**: [`memora/memora/doctype/game_player_device/`](../../memora/memora/doctype/game_player_device/)

**Purpose**: Tracks player devices for multi-device support.

#### Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `player` | Link (User) | Yes | Player |
| `device_id` | Data | Yes | Unique device ID |
| `device_type` | Select | Yes | Device type (mobile, tablet, desktop) |
| `device_name` | Data | No | Device name |
| `last_active` | Datetime | No | Last active timestamp |

---

## DocType Relationships

### Hierarchy Diagram

```
Game Academic Grade
    └── Game Academic Stream
            └── Game Academic Plan
                    └── Game Subject
                            ├── Game Learning Track
                            │       └── Game Unit
                            │               └── Game Lesson
                            │                       └── Game Stage
                            └── Game Topic
                                    └── Game Lesson
```

### Player Data Flow

```
User
    ├── Player Profile
    ├── Player Memory Tracker
    ├── Player Subject Score
    ├── Gameplay Session
    └── Game Player Subscription
```

### Subscription Flow

```
Game Sales Item
    └── Game Purchase Request
            └── Game Player Subscription
                    └── Game Subscription Access
```

---

## DocType Best Practices

### Creating New DocTypes

1. **Define Purpose**: Clearly define what the DocType represents
2. **Choose Naming**: Use descriptive, consistent naming conventions
3. **Set Permissions**: Configure appropriate role-based permissions
4. **Add Indexes**: Add indexes for frequently queried fields
5. **Write Tests**: Create comprehensive test coverage

### Modifying Existing DocTypes

1. **Check Dependencies**: Verify no breaking changes to dependent code
2. **Create Migration**: Use Frappe patches for schema changes
3. **Update Tests**: Ensure all tests pass after changes
4. **Document Changes**: Update documentation with modifications

### Performance Considerations

1. **Partitioning**: Use LIST COLUMNS partitioning for large tables (e.g., Player Memory Tracker)
2. **Indexes**: Add composite indexes for common query patterns
3. **Caching**: Implement Redis caching for frequently accessed data
4. **Archival**: Archive old data to maintain performance

---

**Last Updated**: 2026-01-20
**Frappe Version**: Compatible with Frappe v15+


# Memora Services Documentation

Complete reference for all Memora business logic services.

## Table of Contents

- [Overview](#overview)
- [Service Architecture](#service-architecture)
- [SRS Services](#srs-services)
  - [SRS Redis Manager](#srs-redis-manager)
  - [SRS Persistence](#srs-persistence)
  - [SRS Archiver](#srs-archiver)
  - [SRS Reconciliation](#srs-reconciliation)
- [Infrastructure Services](#infrastructure-services)
  - [Partition Manager](#partition-manager)
- [Service Best Practices](#service-best-practices)

## Overview

Services in Memora encapsulate business logic separate from API endpoints and DocTypes. They handle complex operations like SRS algorithms, caching, archival, and data persistence.

### Service Layer Benefits

- **Separation of Concerns**: Business logic isolated from API layer
- **Reusability**: Services can be called from multiple endpoints
- **Testability**: Easier to unit test in isolation
- **Maintainability**: Clear boundaries and responsibilities

### File Structure

```
memora/services/
├── __init__.py
├── srs_redis_manager.py      # Redis operations for SRS
├── srs_persistence.py        # Async database persistence
├── srs_archiver.py           # Season archival
├── srs_reconciliation.py     # Cache consistency
└── partition_manager.py      # Database partitioning
```

## Service Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    API Layer                               │
│  (reviews.py, sessions.py, srs.py, etc.)                 │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│                  Service Layer                             │
│  ┌──────────────┬──────────────┬──────────────┐         │
│  │  Redis       │  Persistence  │   Archiver   │         │
│  │  Manager     │   Service     │              │         │
│  └──────────────┴──────────────┴──────────────┘         │
└────────────────────┬────────────────────────────────────────┘
                     │
        ┌────────────┴────────────┐
        │                         │
        ▼                         ▼
┌───────────────┐         ┌──────────────┐
│     Redis     │         │  PostgreSQL  │
│    (Cache)    │         │  (Database)  │
└───────────────┘         └──────────────┘
```

## SRS Services

### SRS Redis Manager

**Module**: [`memora/services/srs_redis_manager.py`](../../memora/services/srs_redis_manager.py)

**Purpose**: Manages Redis Sorted Sets for SRS scheduling using high-performance ZSET operations.

#### Key Concepts

- **Key Format**: `srs:{user_email}:{season_name}`
- **Score**: Unix timestamp of `next_review_date`
- **Member**: Question ID (string)
- **TTL**: 30 days for automatic cleanup of inactive users

#### Class: SRSRedisManager

```python
class SRSRedisManager:
    """Manages Redis Sorted Sets for SRS scheduling"""
    
    DEFAULT_TTL = 30 * 24 * 60 * 60  # 30 days
    DEFAULT_REDIS_URL = "redis://localhost:13000"
```

#### Methods

##### `is_available() -> bool`

Check if Redis is responsive.

**Returns**: `True` if Redis is available, `False` otherwise

**Example**:
```python
manager = SRSRedisManager()
if manager.is_available():
    # Use Redis
    pass
else:
    # Fall back to database
    pass
```

---

##### `add_item(user, season, question_id, next_review_ts, ttl=None) -> bool`

Add or update a question's review schedule in Redis.

**Parameters**:
- `user` (str): User email or ID
- `season` (str): Season name
- `question_id` (str): UUID of question
- `next_review_ts` (float): Unix timestamp of next review date
- `ttl` (int, optional): Time-to-live in seconds

**Returns**: `True` if successful, `False` otherwise

**Example**:
```python
manager = SRSRedisManager()
manager.add_item(
    user="user@example.com",
    season="2024-2025",
    question_id="q-123",
    next_review_ts=time.time() + 86400  # 1 day from now
)
```

---

##### `get_due_items(user, season, limit=20) -> List[str]`

Get question IDs due for review.

**Parameters**:
- `user` (str): User email or ID
- `season` (str): Season name
- `limit` (int): Maximum number of items to return

**Returns**: List of question IDs due for review

**Example**:
```python
due_questions = manager.get_due_items(
    user="user@example.com",
    season="2024-2025",
    limit=15
)
```

---

##### `get_due_items_with_rehydration(user, season, limit=20) -> Tuple[List[str], bool]`

Get due items with automatic cache rehydration on miss.

**Parameters**:
- `user` (str): User email or ID
- `season` (str): Season name
- `limit` (int): Maximum number of items to return

**Returns**: Tuple of (due_items, was_rehydrated)

**Example**:
```python
items, was_rehydrated = manager.get_due_items_with_rehydration(
    user="user@example.com",
    season="2024-2025",
    limit=15
)
if was_rehydrated:
    # Cache was loaded from database
    pass
```

---

##### `add_batch(user, season, items, ttl=None) -> bool`

Add multiple items to review schedule in a single operation.

**Parameters**:
- `user` (str): User email or ID
- `season` (str): Season name
- `items` (Dict[str, float]): Dictionary mapping question_id -> next_review_ts
- `ttl` (int, optional): Time-to-live in seconds

**Returns**: `True` if successful, `False` otherwise

**Example**:
```python
items = {
    "q-123": time.time() + 86400,
    "q-124": time.time() + 172800,
    "q-125": time.time() + 259200
}
manager.add_batch(
    user="user@example.com",
    season="2024-2025",
    items=items
)
```

---

##### `remove_item(user, season, question_id) -> bool`

Remove a question from review schedule.

**Parameters**:
- `user` (str): User email or ID
- `season` (str): Season name
- `question_id` (str): UUID of question

**Returns**: `True` if successful, `False` otherwise

---

##### `clear_user_cache(user, season) -> bool`

Clear all review schedule data for a user-season pair.

**Parameters**:
- `user` (str): User email or ID
- `season` (str): Season name

**Returns**: `True` if successful, `False` otherwise

---

##### `get_cache_stats(user, season) -> Dict`

Get statistics about a user's cache.

**Parameters**:
- `user` (str): User email or ID
- `season` (str): Season name

**Returns**: Dictionary with statistics:
- `total_items`: Total items in cache
- `due_items`: Number of due items
- `memory_usage_bytes`: Memory used by key

---

#### Module Functions

##### `rebuild_season_cache(season_name, batch_size=1000) -> Dict`

Rebuild Redis cache for an entire season with progress tracking.

**Parameters**:
- `season_name` (str): Name of season to rebuild cache for
- `batch_size` (int): Number of records to process per batch

**Returns**: Dictionary with rebuild results:
- `total_records`: Total records processed
- `total_users`: Number of unique users
- `total_keys`: Number of Redis keys created
- `status`: "completed" or "failed"

**Optimization**: Uses Keyset Pagination (Seek Method) for O(1) performance regardless of table size.

**Example**:
```python
result = rebuild_season_cache("2024-2025", batch_size=1000)
print(f"Processed {result['total_records']} records")
```

---

### SRS Persistence

**Module**: [`memora/services/srs_persistence.py`](../../memora/services/srs_persistence.py)

**Purpose**: Handles asynchronous database persistence for SRS review responses with retry logic and audit logging.

#### Key Features

- **Async Persistence**: Background job processing
- **Retry Logic**: Exponential backoff with max retries
- **Audit Logging**: Logs all persistence operations
- **Idempotent Design**: Prevents duplicate writes
- **Race Condition Handling**: Uses DB constraints

#### Class: SRSPersistenceService

```python
class SRSPersistenceService:
    """Service for asynchronous SRS data persistence"""
    
    MAX_RETRIES = 3
    RETRY_DELAY_BASE = 1  # seconds
    RETRY_DELAY_MAX = 60  # seconds
    IDEMPOTENCY_WINDOW = 300  # 5 minutes
```

#### Methods

##### `persist_review_batch(responses, user, season, retry_count=0) -> Dict`

Persist a batch of review responses to database.

**Parameters**:
- `responses` (List[Dict]): List of review responses
  - `question_id` (str): Question ID
  - `new_stability` (float): New stability level
  - `new_next_review_date` (datetime): Next review date
  - `subject` (str, optional): Subject
  - `topic` (str, optional): Topic
- `user` (str): User email or ID
- `season` (str): Season name
- `retry_count` (int): Current retry attempt

**Returns**: Dictionary with:
- `success`: Whether operation succeeded
- `processed_count`: Number of records processed
- `failed_count`: Number of records failed
- `errors`: List of error messages

**Example**:
```python
service = SRSPersistenceService()
responses = [
    {
        "question_id": "q-123",
        "new_stability": 2.5,
        "new_next_review_date": datetime(2026, 1, 21),
        "subject": "mathematics",
        "topic": "algebra"
    }
]
result = service.persist_review_batch(
    responses=responses,
    user="user@example.com",
    season="2024-2025"
)
```

**Process**:
1. Try to INSERT new record
2. If duplicate (race condition), UPDATE existing record
3. Check idempotency window (5 minutes)
4. Commit transaction
5. Log audit on errors or retries

---

##### `persist_single_review(response, user, season) -> bool`

Convenience method for single-item persistence.

**Parameters**:
- `response` (Dict): Single review response
- `user` (str): User email or ID
- `season` (str): Season name

**Returns**: `True` if successful, `False` otherwise

---

##### `get_persistence_status(job_id) -> Optional[Dict]`

Get status of a persistence background job.

**Parameters**:
- `job_id` (str): Background job ID

**Returns**: Job status dictionary or `None`

---

### SRS Archiver

**Module**: [`memora/services/srs_archiver.py`](../../memora/services/srs_archiver.py)

**Purpose**: Manages archiving of old season data to cold storage.

#### Key Features

- **Transactional Operations**: Ensures data integrity
- **Bulk SQL Operations**: High-performance copy/delete
- **Cache Cleanup**: Clears Redis for archived seasons
- **Retention Policy**: 3-year retention before deletion
- **Auto-Archive**: Scheduled archival of eligible seasons

#### Class: SRSArchiver

```python
class SRSArchiver:
    """Manages archiving of old season data"""
    
    RETENTION_DAYS = 3 * 365  # 3 years
```

#### Methods

##### `archive_season(season_name) -> Dict`

Archive all memory tracker records for a season.

**Parameters**:
- `season_name` (str): Name of season to archive

**Returns**: Dictionary with:
- `success`: Whether operation succeeded
- `archived_count`: Number of records archived
- `season`: Season name
- `error`: Error message if failed

**Process**:
1. Validate season exists and is not active
2. Start database transaction
3. Bulk copy records to `Archived Memory Tracker`
4. Bulk delete from `Player Memory Tracker`
5. Commit transaction
6. Clear Redis cache for season

**Example**:
```python
archiver = SRSArchiver()
result = archiver.archive_season("2023-2024")
if result["success"]:
    print(f"Archived {result['archived_count']} records")
```

---

##### `process_auto_archive() -> Dict`

Process auto-archive for eligible seasons.

**Returns**: Dictionary with:
- `success`: Whether operation succeeded
- `archived_seasons`: Number of seasons archived
- `failed_seasons`: List of failed seasons

**Eligibility**:
- Season has `auto_archive` flag set
- Season is not active
- Season end date has passed

---

##### `flag_eligible_for_deletion() -> Dict`

Flag archived records eligible for deletion (3+ years old).

**Returns**: Dictionary with:
- `success`: Whether operation succeeded
- `flagged_count`: Number of records flagged
- `cutoff_date`: Date threshold used

**Process**:
1. Calculate cutoff date (3 years ago)
2. Bulk update `eligible_for_deletion` flag
3. Return count of affected records

---

##### `get_archive_status(season_name) -> Dict`

Get archive status for a season.

**Parameters**:
- `season_name` (str): Season name

**Returns**: Dictionary with:
- `season`: Season name
- `is_active`: Whether season is active
- `auto_archive`: Whether auto-archive is enabled
- `end_date`: Season end date
- `active_records`: Count of active records
- `archived_records`: Count of archived records
- `eligible_for_deletion`: Count of records marked for deletion
- `total_records`: Total records (active + archived)

---

##### `delete_eligible_records(season_name=None, confirm=False) -> Dict`

Delete archived records marked for deletion.

**Parameters**:
- `season_name` (str, optional): Filter by season
- `confirm` (bool): Must be `True` to confirm deletion

**Returns**: Dictionary with:
- `success`: Whether operation succeeded
- `deleted_count`: Number of records deleted
- `error`: Error message if failed

**Safety**: Requires explicit confirmation to prevent accidental deletion.

---

### SRS Reconciliation

**Module**: [`memora/services/srs_reconciliation.py`](../../memora/services/srs_reconciliation.py)

**Purpose**: Ensures cache consistency between Redis and PostgreSQL.

#### Key Features

- **Cache Consistency**: Detects and fixes discrepancies
- **Automatic Correction**: Auto-corrects common issues
- **Audit Logging**: Logs all reconciliation actions
- **Scheduled Execution**: Runs daily via background job

#### Typical Use Cases

1. **Cache Miss**: Redis empty but database has records
2. **Stale Cache**: Redis has outdated data
3. **Orphaned Records**: Database records without cache entries
4. **Ghost Records**: Cache entries without database records

#### Reconciliation Process

```
1. Fetch all records from database for user-season
2. Fetch all records from Redis cache
3. Compare and identify discrepancies:
   - Missing in Redis → Add to cache
   - Missing in database → Remove from cache
   - Timestamp mismatch → Update cache
4. Log all corrections
5. Return summary
```

---

## Infrastructure Services

### Partition Manager

**Module**: [`memora/services/partition_manager.py`](../../memora/services/partition_manager.py)

**Purpose**: Manages database partitioning for performance optimization.

#### Key Concepts

- **Partitioning Type**: LIST COLUMNS
- **Partition Key**: `season` field
- **Automatic Creation**: New partitions created for new seasons
- **Query Optimization**: Queries filtered by season use partition pruning

#### Benefits

- **Performance**: Queries only scan relevant partitions
- **Maintenance**: Can archive/drop old partitions
- **Scalability**: Supports millions of records efficiently

#### Typical Operations

##### Create Partition

```python
from memora.services.partition_manager import create_partition

create_partition("2024-2025")
```

##### Drop Partition

```python
from memora.services.partition_manager import drop_partition

drop_partition("2020-2021")
```

##### List Partitions

```python
from memora.services.partition_manager import list_partitions

partitions = list_partitions("Player Memory Tracker")
```

---

## Service Best Practices

### 1. Error Handling

Always wrap service operations in try-except blocks:

```python
try:
    result = service.method()
except Exception as e:
    frappe.log_error(str(e), "ServiceName.method")
    return {"success": False, "error": str(e)}
```

### 2. Transaction Management

Use database transactions for multi-step operations:

```python
frappe.db.begin()
try:
    # Operation 1
    # Operation 2
    frappe.db.commit()
except Exception as e:
    frappe.db.rollback()
    raise
```

### 3. Batch Operations

Use batch operations for better performance:

```python
# Good: Batch insert
items = {"q-1": ts1, "q-2": ts2, "q-3": ts3}
redis_manager.add_batch(user, season, items)

# Avoid: Individual inserts
for question_id, ts in items.items():
    redis_manager.add_item(user, season, question_id, ts)
```

### 4. Logging

Log errors and important events:

```python
frappe.log_error(
    f"Failed to persist {len(responses)} records: {str(e)}",
    "SRSPersistenceService.persist_review_batch"
)
```

### 5. Idempotency

Design services to be idempotent:

```python
# Check if already processed
if already_processed(job_id):
    return {"status": "already_processed"}

# Process
result = process_job(job_id)
```

### 6. Retry Logic

Implement exponential backoff for retries:

```python
if retry_count < MAX_RETRIES:
    delay = min(RETRY_DELAY_BASE * (2 ** retry_count), RETRY_DELAY_MAX)
    time.sleep(delay)
    # Retry
```

### 7. Cache Invalidation

Invalidate cache when data changes:

```python
# Update database
update_record(record_id)

# Clear cache
redis_manager.clear_user_cache(user, season)
```

### 8. Performance Monitoring

Track service performance:

```python
import time

start = time.time()
result = service.method()
duration = time.time() - start

if duration > 1.0:
    frappe.logger().warning(f"Slow operation: {duration:.2f}s")
```

---

## Testing Services

### Unit Testing

```python
def test_redis_manager_add_item():
    manager = SRSRedisManager()
    result = manager.add_item(
        user="test@example.com",
        season="2024-2025",
        question_id="q-123",
        next_review_ts=time.time() + 86400
    )
    assert result == True
```

### Integration Testing

```python
def test_persistence_with_redis():
    # Add to Redis
    redis_manager.add_item(...)
    
    # Persist to database
    persistence_service.persist_review_batch(...)
    
    # Verify database
    record = frappe.get_doc("Player Memory Tracker", filters={...})
    assert record is not None
```

---

## Scheduled Jobs

Services can be registered as scheduled jobs in [`memora/hooks.py`](../../memora/hooks.py):

```python
scheduler_events = {
    "daily": [
        "memora.services.srs_archiver.process_auto_archive",
        "memora.services.srs_reconciliation.reconcile_cache_with_database"
    ],
    "weekly": [
        "memora.services.srs_archiver.flag_eligible_for_deletion"
    ]
}
```

---

**Last Updated**: 2026-01-20