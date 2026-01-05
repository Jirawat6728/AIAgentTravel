# AI Agent Architecture

## Overview

This AI Travel Agent implements a comprehensive agent architecture with the following core components:

**LLM + Memory + State + Intent + Controller + Identity = AI**

## Core Components

### 1. Persistent Identity
- **Purpose**: Maintains consistent user identity and preferences across sessions
- **Implementation**: 
  - User context stored in MongoDB (`context.py`)
  - User profile persistence (`users_repo.py`)
  - Session management (`sessions_repo.py`)
- **Key Features**:
  - User-specific conversation context
  - Preference learning over time
  - Cross-session continuity

### 2. Working Memory
- **Purpose**: Maintains active context for the current conversation session
- **Implementation**:
  - `backend/core/context.py` - Context management system
  - `backend/core/state.py` - Agent state tracking
  - MongoDB sessions for persistence
- **Key Features**:
  - Travel slots (origin, destination, dates, passengers)
  - Current plan state
  - Search results caching
  - Last agent state and steps
  - Trip history

### 3. Memory Selection
- **Purpose**: Intelligently retrieves relevant context from stored memory
- **Implementation**:
  - Context retrieval based on user_id and trip_id
  - Selective memory updates (write_memory flag)
  - Last travel slots and plan choices preservation
- **Key Features**:
  - Automatic context restoration
  - Selective memory writes (refresh vs. new messages)
  - Memory cooldown mechanisms

### 4. Intent Understanding
- **Purpose**: Understands user intent from natural language messages
- **Implementation**:
  - `backend/services/slot_intent_service.py` - Slot-level intent detection
  - `backend/services/single_item_intent_service.py` - Single-item intent (flight/hotel only)
  - Gemini LLM for natural language understanding
- **Key Features**:
  - Intent classification (edit, search, confirm, etc.)
  - Slot-specific intent (flight, hotel, transport, dates, pax)
  - Segment-level editing intent
  - Context-aware intent resolution

### 5. Self-Directed Flow
- **Purpose**: Agent directs its own workflow based on context and intent
- **Implementation**:
  - `backend/core/orchestrator.py` - Main orchestration logic
  - Multi-step agent flow with state transitions
  - Conditional execution paths based on context
- **Key Features**:
  - Automatic workflow progression
  - State-based decision making
  - Multi-step plan building
  - Automatic fallback handling

### 6. Tool-Aware Intelligence
- **Purpose**: Agent understands and uses available tools/services effectively
- **Implementation**:
  - `backend/services/amadeus_service.py` - Flight and hotel search
  - `backend/services/google_maps_service.py` - Location services
  - `backend/services/gemini_service.py` - LLM integration
  - `backend/core/plan_builder.py` - Plan construction logic
- **Key Features**:
  - Tool selection based on intent
  - Parallel service calls where applicable
  - Result aggregation and processing
  - Error handling and retry logic

## Architecture Flow

```
User Message
    ↓
Intent Understanding (detect intent)
    ↓
Memory Selection (retrieve relevant context)
    ↓
Controller (orchestrator.py)
    ↓
Tool Selection & Execution
    ├── Amadeus API (flights/hotels)
    ├── Google Maps API (locations)
    ├── Gemini LLM (natural language)
    └── Plan Builder (plan construction)
    ↓
Working Memory Update (save context)
    ↓
Response Generation
    ↓
Persistent Identity Update (user preferences)
```

## Component Interactions

### Context Flow
1. **Initial Request**: User message arrives
2. **Identity Retrieval**: Get user context from persistent storage
3. **Memory Selection**: Retrieve relevant working memory
4. **Intent Detection**: Analyze user intent
5. **Controller Decision**: Orchestrator decides workflow
6. **Tool Execution**: Execute appropriate tools/services
7. **Memory Update**: Update working memory with results
8. **Response**: Generate and return response
9. **Identity Update**: Update user preferences/context

### State Management
- **Agent State**: Tracks current agent step, intent, and workflow stage
- **Travel Slots**: Current trip requirements (origin, destination, dates, etc.)
- **Plan State**: Current selected plan and choices
- **Search Results**: Cached search results from APIs

### Memory Hierarchy
1. **Persistent Storage** (MongoDB):
   - User profiles
   - Session history
   - Trip history
   - Long-term preferences

2. **Working Memory** (Context):
   - Current conversation state
   - Active travel slots
   - Current plan
   - Search results
   - Agent state

3. **Ephemeral State** (In-memory):
   - Current request state
   - Temporary processing data
   - Cooldown timers

## Key Design Principles

1. **Separation of Concerns**: Each component has a single responsibility
2. **State Persistence**: Critical state is persisted for continuity
3. **Intent-Driven**: Workflow is determined by user intent
4. **Tool Abstraction**: Tools are abstracted and can be swapped
5. **Error Resilience**: Graceful degradation and error handling
6. **Scalability**: Architecture supports horizontal scaling

## Implementation Files

- **Identity**: `backend/repos/users_repo.py`, `backend/core/auth.py`
- **Memory**: `backend/core/context.py`, `backend/db/repos/sessions_repo.py`
- **Memory Selection**: `backend/core/context.py` (get_user_ctx)
- **Intent**: `backend/services/slot_intent_service.py`, `backend/services/single_item_intent_service.py`
- **Controller**: `backend/core/orchestrator.py`
- **State**: `backend/core/state.py`, `backend/core/models.py`
- **Tools**: `backend/services/amadeus_service.py`, `backend/services/gemini_service.py`, `backend/core/plan_builder.py`

## Development Levels

The AI Agent architecture is designed to evolve through three levels of sophistication:

### 🥉 Level 1 – เลิกเป็น chatbot

**Goal**: Move beyond simple chatbot pattern

**Features**:
- ✅ **Conversation State**: Track conversation state beyond single turn
  - Implementation: `backend/core/context.py`, `backend/core/state.py`
  - Active conversation context, travel slots, current plan state
  
- ✅ **Intent + Mode**: Structured intent understanding and operation modes
  - Implementation: `backend/services/slot_intent_service.py`, `backend/services/single_item_intent_service.py`
  - Intent classification (edit, search, confirm, etc.)
  - Mode detection (flight_only, hotel_only, full_trip)
  
- ✅ **Structured Output**: Return structured data instead of free-form text
  - Implementation: `backend/core/orchestrator.py`, response schema
  - Structured JSON responses with `travel_slots`, `plan_choices`, `agent_state`
  - Type-safe response format with Pydantic models

**Current Status**: ✅ Implemented

### 🥈 Level 2 – เหมือน Gemini

**Goal**: Achieve Gemini-like intelligence and proactivity

**Features**:
- ✅ **Memory Policy**: Define what to remember and for how long
  - Implementation: `backend/core/memory_policy.py`
  - Priority-based memory retention (Critical, High, Medium, Low)
  - Automatic cleanup of expired memory items
  - Timestamp tracking for memory items
  
- ✅ **Controller + Workflow**: Orchestrate multi-step workflows
  - Implementation: `backend/core/orchestrator.py`
  - Multi-step plan building workflow
  - Conditional execution paths
  - State machine for workflow progression
  
- ✅ **Proactive Flow**: Agent takes initiative beyond user requests
  - Implementation: `backend/core/proactive_flow.py`
  - Context-aware suggestion generation
  - Proactive messages to guide users
  - Anticipatory suggestions based on state

**Current Status**: ✅ Fully Implemented

### 🥇 Level 3 – AI Agent เต็มรูปแบบ

**Goal**: Full autonomous AI Agent capabilities

**Features**:
- 🔄 **Long-term Memory**: Persistent memory across sessions and time
  - Current: Session-based memory
  - Future: Long-term user preference learning
  - Cross-session memory retrieval
  - Temporal context awareness
  
- 🔄 **Persona + Style per User**: Personalized agent personality and communication style
  - Current: Single agent persona
  - Future: User-specific persona adaptation
  - Style learning from user interactions
  - Communication preference personalization
  
- 🔄 **Tool Reasoning + Audit**: Intelligent tool selection and usage auditing
  - Current: Direct tool calls based on intent
  - Future: Reasoning about which tools to use
  - Tool usage optimization
  - Audit trail for tool invocations
  - Tool chain planning

**Current Status**: 🔄 Planned for Future Implementation

## Level Comparison

| Feature | Level 1 | Level 2 | Level 3 |
|---------|---------|---------|---------|
| Conversation State | ✅ | ✅ | ✅ |
| Intent + Mode | ✅ | ✅ | ✅ |
| Structured Output | ✅ | ✅ | ✅ |
| Memory Policy | ❌ | ✅ | ✅ |
| Controller + Workflow | ⚠️ | ✅ | ✅ |
| Proactive Flow | ❌ | ✅ | ✅ |
| Long-term Memory | ❌ | ❌ | 🔄 |
| Persona + Style | ❌ | ❌ | 🔄 |
| Tool Reasoning + Audit | ❌ | ❌ | 🔄 |

**Legend**:
- ✅ Fully Implemented
- ⚠️ Partially Implemented
- 🔄 Planned/Future
- ❌ Not Implemented

## Summary

This architecture implements a complete AI agent system where:

- **LLM** (Gemini) provides natural language understanding and generation
- **Memory** (Context system) maintains conversation state
- **State** (AgentState) tracks workflow progression
- **Intent** (Intent services) understands user goals
- **Controller** (Orchestrator) coordinates all components
- **Identity** (User context) provides personalization

Together, these components create a self-directed, context-aware AI agent capable of complex multi-step travel planning tasks.

**Current Level**: 🥇 Level 3 (Complete - Fully Integrated)

**Status**: All Level 3 features are now integrated into the unified orchestrator. No feature flag needed!

The system has successfully moved beyond a simple chatbot pattern (Level 1) and is progressing toward Gemini-like intelligence (Level 2), with plans for full autonomous agent capabilities (Level 3).

