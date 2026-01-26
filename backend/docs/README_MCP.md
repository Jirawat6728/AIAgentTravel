# 🚀 Model Context Protocol (MCP) Integration

## Overview

The AI Travel Agent now supports **Model Context Protocol (MCP)**, enabling Gemini LLM to directly call Amadeus and Google Maps APIs through function calling.

## ✨ Features

- **7 Production-Ready Tools**: Flights, Hotels, Transfers, Activities, Geocoding, Airport Lookup, Place Details
- **Automatic Tool Selection**: LLM decides which tools to use based on user input
- **REST API Endpoints**: All tools exposed via FastAPI for testing
- **Error Handling**: Graceful fallbacks when APIs fail
- **Performance Optimized**: Caching, result limiting, timeout management

## 🎯 Quick Start

### 1. Setup

```bash
# Install dependencies
pip install -r requirements.txt

# Configure .env
GEMINI_API_KEY=your_key
AMADEUS_API_KEY=your_key
AMADEUS_API_SECRET=your_secret
GOOGLE_MAPS_API_KEY=your_key
```

### 2. Test

```bash
cd backend
python test_mcp.py
```

### 3. Use

```python
from app.services.llm_with_mcp import LLMServiceWithMCP

llm = LLMServiceWithMCP()
result = await llm.generate_with_tools(
    prompt="Find flights from Bangkok to Tokyo on Feb 15",
    system_prompt="You are a travel assistant."
)

print(result["text"])  # AI response with real data
```

## 📚 Documentation

- **Quick Start**: [`docs/MCP_QUICKSTART.md`](./docs/MCP_QUICKSTART.md)
- **Full Guide**: [`docs/MCP_INTEGRATION.md`](./docs/MCP_INTEGRATION.md)
- **Examples**: [`examples/mcp_usage_example.py`](./examples/mcp_usage_example.py)

## 🛠️ Available Tools

| Tool | API | Description |
|------|-----|-------------|
| `search_flights` | Amadeus | Search flight offers |
| `search_hotels` | Amadeus | Search hotel offers |
| `search_transfers` | Amadeus | Search ground transfers |
| `search_activities` | Amadeus | Search tours & activities |
| `geocode_location` | Google Maps | Get coordinates |
| `find_nearest_airport` | Google Maps + Amadeus | Find IATA code |
| `get_place_details` | Google Maps | Get place info |

## 🔌 API Endpoints

```bash
# List all tools
GET /api/mcp/tools

# Execute any tool
POST /api/mcp/execute
{
  "tool_name": "search_flights",
  "parameters": {...}
}

# Convenience endpoints
POST /api/mcp/search/flights
POST /api/mcp/search/hotels
POST /api/mcp/search/transfers
POST /api/mcp/search/activities
POST /api/mcp/geocode
POST /api/mcp/airport
```

## 📊 Architecture

```
User Request
    ↓
Gemini LLM (with MCP)
    ↓
MCPToolExecutor
    ↓
TravelOrchestrator
    ↓
Amadeus API / Google Maps API
    ↓
Formatted Results
    ↓
LLM Final Response
```

## 🧪 Testing

```bash
# Full test suite
python test_mcp.py

# Examples
python examples/mcp_usage_example.py

# Individual tool
curl -X POST http://localhost:8000/api/mcp/geocode \
  -H "Content-Type: application/json" \
  -d '{"place_name": "Tokyo Tower"}'
```

## 🎓 Examples

### Direct Tool Call
```python
from app.services.mcp_server import mcp_executor

result = await mcp_executor.execute_tool(
    "search_flights",
    {
        "origin": "BKK",
        "destination": "NRT",
        "departure_date": "2025-02-15",
        "adults": 2
    }
)
```

### LLM with Tools
```python
from app.services.llm_with_mcp import LLMServiceWithMCP

llm = LLMServiceWithMCP()
result = await llm.generate_with_tools(
    prompt="Plan a 3-day trip to Tokyo from Feb 15-17",
    system_prompt="You are a travel planner. Use tools to search."
)
```

### Integration with Agent
```python
from app.engine.agent import TravelAgent
from app.services.llm_with_mcp import LLMServiceWithMCP

llm_with_mcp = LLMServiceWithMCP()
agent = TravelAgent(storage, llm_service=llm_with_mcp)

response = await agent.run_turn(
    session_id="user::trip",
    user_input="I want to fly to Tokyo"
)
```

## 🔧 Configuration

```python
# app/core/config.py
gemini_timeout_seconds = 60  # LLM timeout
gemini_max_retries = 3  # Retry attempts

# In code
result = await llm.generate_with_tools(
    prompt="...",
    max_tool_calls=5,  # Max iterations
    temperature=0.7,
    max_tokens=2000
)
```

## 📈 Performance

- **Caching**: Google Maps results cached in memory
- **Result Limiting**: Max 5 results per tool
- **Parallel Calls**: Future enhancement
- **Timeout Management**: 60s default timeout

## 🐛 Troubleshooting

### No tools loaded
```bash
python -c "from app.services.mcp_server import ALL_MCP_TOOLS; print(len(ALL_MCP_TOOLS))"
# Should output: 7
```

### Tool execution fails
```bash
# Test Amadeus
curl -X POST https://test.api.amadeus.com/v1/security/oauth2/token \
  -d "grant_type=client_credentials&client_id=KEY&client_secret=SECRET"

# Test Google Maps
curl "https://maps.googleapis.com/maps/api/geocode/json?address=Bangkok&key=KEY"
```

### LLM not calling tools
Ensure you're using `LLMServiceWithMCP`, not `LLMService`:
```python
# ✓ Correct
from app.services.llm_with_mcp import LLMServiceWithMCP
llm = LLMServiceWithMCP()
```

## 📝 Logging

All MCP operations are logged:
```
INFO - Executing MCP tool: search_flights with params: {...}
INFO - LLM requested tool: search_flights
INFO - MCP iteration 1/5
```

Check logs: `backend/data/logs/`

## 🚀 Next Steps

1. Read full docs: [`docs/MCP_INTEGRATION.md`](./docs/MCP_INTEGRATION.md)
2. Try examples: [`examples/mcp_usage_example.py`](./examples/mcp_usage_example.py)
3. Test API: `http://localhost:8000/docs`
4. Integrate with your agent

## 📄 License

Same as main project

---

**Built with**: Gemini LLM, Amadeus API, Google Maps API, FastAPI, Python 3.12+

