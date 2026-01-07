# MongoDB Database Design

## Overview

Production-grade MongoDB schema design for AI Travel Agent system.

## Database Structure

### Database Name
`travel_agent` (configurable via `MONGODB_DATABASE` env var)

## Collections

### 1. `sessions` Collection

**Purpose**: Store user session state and trip plans

**Schema**:
```json
{
  "_id": ObjectId,
  "session_id": "user123::chat1",  // Unique, indexed
  "user_id": "user123",              // Indexed
  "trip_plan": {
    "flights": [
      {
        "status": "pending|searching|selecting|confirmed",
        "requirements": {},
        "options_pool": [],
        "selected_option": null
      }
    ],
    "accommodations": [],
    "ground_transport": []
  },
  "title": "การเดินทางไป Tokyo",     // Optional chat title
  "created_at": ISODate,
  "last_updated": ISODate,           // Indexed (descending)
  "metadata": {}
}
```

**Indexes**:
- `session_id` (unique)
- `user_id`
- `last_updated` (descending)
- `user_id + last_updated` (compound)

**Use Cases**:
- Store current trip planning state
- Track conversation sessions
- Quick lookup by session_id or user_id

---

### 2. `users` Collection

**Purpose**: Store user profile information

**Schema**:
```json
{
  "_id": ObjectId,
  "user_id": "user123",              // Unique, indexed
  "email": "user@example.com",        // Unique, sparse index
  "name": "John Doe",
  "created_at": ISODate,
  "last_active": ISODate,             // Indexed (descending)
  "metadata": {
    "preferences": {},
    "booking_history": []
  }
}
```

**Indexes**:
- `user_id` (unique)
- `email` (unique, sparse)
- `last_active` (descending)

**Use Cases**:
- User profile management
- Preference storage
- Activity tracking

---

### 3. `conversations` Collection

**Purpose**: Store conversation history for analytics and context

**Schema**:
```json
{
  "_id": ObjectId,
  "session_id": "user123::chat1",     // Indexed
  "user_id": "user123",               // Indexed
  "messages": [
    {
      "role": "user|assistant",
      "content": "ไป Tokyo",
      "timestamp": ISODate,
      "metadata": {}
    }
  ],
  "created_at": ISODate,
  "updated_at": ISODate               // Indexed (descending)
}
```

**Indexes**:
- `session_id`
- `user_id`
- `updated_at` (descending)
- `session_id + updated_at` (compound)

**Use Cases**:
- Conversation history
- Analytics and insights
- Context retrieval for future sessions

---

### 4. `bookings` Collection

**Purpose**: Store confirmed bookings

**Schema**:
```json
{
  "_id": ObjectId,
  "booking_id": "BOOK-2024-001",      // Unique, indexed
  "session_id": "user123::chat1",     // Indexed
  "user_id": "user123",                // Indexed
  "trip_plan": {
    // Complete trip plan with all confirmed segments
  },
  "status": "confirmed|pending|cancelled",
  "total_price": 50000.00,
  "created_at": ISODate,               // Indexed (descending)
  "confirmed_at": ISODate,
  "metadata": {
    "payment_status": "paid",
    "confirmation_codes": {}
  }
}
```

**Indexes**:
- `booking_id` (unique)
- `session_id`
- `user_id`
- `status`
- `created_at` (descending)
- `user_id + created_at` (compound)

**Use Cases**:
- Booking management
- Order history
- Payment tracking

---

## Data Relationships

```
users (1) ──< (many) sessions
sessions (1) ──< (many) conversations
sessions (1) ──< (many) bookings
```

## Index Strategy

### Performance Considerations

1. **Frequent Queries**:
   - `session_id` lookup → Unique index
   - `user_id` + `last_updated` → Compound index for user's recent sessions

2. **Time-based Queries**:
   - `last_updated`, `created_at`, `updated_at` → Descending indexes

3. **Search Patterns**:
   - User's sessions → `user_id` index
   - Recent bookings → `user_id + created_at` compound index

## Migration from JSON Storage

### Migration Script

```python
# Migrate from JSON files to MongoDB
async def migrate_json_to_mongodb():
    json_storage = JsonFileStorage()
    mongo_storage = MongoStorage()
    
    # Get all JSON session files
    for session_file in json_storage.sessions_dir.glob("*.json"):
        session_id = extract_session_id(session_file)
        session = await json_storage.get_session(session_id)
        await mongo_storage.save_session(session)
```

## Environment Variables

```env
MONGODB_URI=mongodb://localhost:27017
MONGODB_DATABASE=travel_agent
```

## Connection Pooling

- Motor (async MongoDB driver) handles connection pooling automatically
- Default pool size: 100 connections
- Configure via connection string: `mongodb://host:port/?maxPoolSize=200`

## Backup Strategy

1. **Regular Backups**: Daily MongoDB backups
2. **Point-in-Time Recovery**: Enable oplog for point-in-time recovery
3. **Replication**: Use MongoDB replica sets for high availability

## Security

1. **Authentication**: Enable MongoDB authentication
2. **Authorization**: Use role-based access control
3. **Encryption**: Enable TLS/SSL for connections
4. **Network**: Restrict network access to MongoDB

## Monitoring

1. **Performance**: Monitor query performance and slow queries
2. **Storage**: Track collection sizes and growth
3. **Connections**: Monitor connection pool usage
4. **Indexes**: Ensure indexes are being used effectively

