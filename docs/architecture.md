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
