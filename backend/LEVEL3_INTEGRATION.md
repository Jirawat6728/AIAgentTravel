# Level 3 Integration Guide

## Overview

Level 3 Architecture (Planner/Executor/Narrator) is now fully integrated into the main orchestrator.
All Level 3 features are enabled by default - no feature flag needed!

## Architecture Flow

Level 3 orchestrator is now integrated into `backend/core/orchestrator.py`. The system automatically selects V2 or V3 based on the `USE_V3_ORCHESTRATOR` flag.

```
User Message
    ↓
[Planner - LLM #1] (V3 only)
    ↓ Analyze intent, constraints, missing info
    ↓
[Decision: Proceed or Ask?]
    ↓
[Executor - Tools] (V3 only)
    ↓ Execute Amadeus search, build plans
    ↓
[Narrator - LLM #2] (V3 only)
    ↓ Generate natural response
    ↓
Response + Reasoning + Memory Suggestions
```

## Components

### 1. Planner (`backend/core/planner.py`)
- Uses LLM to analyze user message
- Extracts goals, constraints, missing info
- Decides whether to proceed or ask a question

### 2. Executor (`backend/core/executor.py`)
- Executes tools based on planner output
- Calls Amadeus search, builds plan choices
- Returns structured results

### 3. Narrator (`backend/core/narrator.py`)
- Uses LLM to generate natural response
- Includes reasoning and memory suggestions
- Creates next action suggestions

### 4. Session Store (`backend/core/session_store.py`)
- Stores agent state persistently
- Tracks message count for auto-summarize

### 5. Conversation Summary (`backend/core/conversation_summary.py`)
- Auto-summarizes every 10 messages
- Reduces token usage for long conversations

### 6. User Profile Memory (`backend/core/user_profile_memory.py`)
- Stores long-term preferences
- Applies preferences to travel slots

## API Changes

### New Response Fields

- `reasoning`: Explanation for recommendations (for reasoning light UI)
- `memory_suggestions`: Array of preferences to remember (for memory toggle UI)

### Memory API

- `POST /api/memory/commit` - Commit memory items
- `GET /api/session/{session_id}` - Get session data

## Frontend Integration

Frontend already supports:
- Reasoning light display
- Memory toggle UI
- Auto-commit preferences

## Testing

1. Enable V3 orchestrator:
   ```bash
   export USE_V3_ORCHESTRATOR=true
   ```

2. Start the backend:
   ```bash
   cd backend && python -m uvicorn main:app --reload
   ```

3. Test in frontend - you should see:
   - More structured responses
   - Reasoning explanations
   - Memory suggestions

## Fallback

If V3 orchestrator fails, the system automatically falls back to V2 orchestrator for stability.

## Migration Path

The system supports gradual migration:
- V2 orchestrator (default) - stable, battle-tested
- V3 orchestrator (opt-in) - new architecture, more intelligent

Both can coexist, allowing for A/B testing and gradual rollout.

