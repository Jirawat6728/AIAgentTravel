# MCP Quick Start Guide

## What is MCP?

**Model Context Protocol (MCP)** enables LLMs to call external APIs and tools directly through function calling. Instead of manually coding API calls, the AI decides when and how to use tools based on user requests.

## Quick Setup

### 1. Install Dependencies

All required packages are already in `requirements.txt`:
```bash
pip install -r requirements.txt
```

### 2. Configure API Keys

Add to your `.env` file:
```bash
# Gemini (required for LLM)
GEMINI_API_KEY=your_gemini_api_key
GEMINI_MODEL_NAME=gemini-1.5-flash

# Amadeus (required for travel tools)
AMADEUS_API_KEY=your_amadeus_key
AMADEUS_API_SECRET=your_amadeus_secret
AMADEUS_ENV=test

# Google Maps (required for location tools)
GOOGLE_MAPS_API_KEY=your_google_maps_key
```

### 3. Test MCP

Run the test script:
```bash
cd backend
python test_mcp.py
```

Expected output:
```
✓ LLM initialized with 7 tools
✓ Response generated
  Tools called: 1
    1. search_flights - Success: True
```

## Available Tools

| Tool | Description | Use Case |
|------|-------------|----------|
| `search_flights` | Search Amadeus flight offers | "Find flights from BKK to NRT" |
| `search_hotels` | Search Amadeus hotel offers | "Find hotels in Tokyo" |
| `search_transfers` | Search ground transfers | "Find taxi from airport to hotel" |
| `search_activities` | Search tours & activities | "Find things to do in Tokyo" |
| `geocode_location` | Get coordinates from place name | "Where is Tokyo Tower?" |
| `find_nearest_airport` | Find IATA code for city | "What's the airport code for Phuket?" |
| `get_place_details` | Get place information | "Tell me about Eiffel Tower" |

## Usage Examples

### Example 1: Direct Tool Call

```python
from app.services.mcp_server import mcp_executor

# Call tool directly
result = await mcp_executor.execute_tool(
    tool_name="search_flights",
    parameters={
        "origin": "BKK",
        "destination": "NRT",
        "departure_date": "2025-02-15",
        "adults": 2
    }
)

print(result["flights"])  # List of flight options
```

### Example 2: LLM with Tools

```python
from app.services.llm_with_mcp import LLMServiceWithMCP

llm = LLMServiceWithMCP()

# LLM decides which tools to use
result = await llm.generate_with_tools(
    prompt="Find me flights from Bangkok to Tokyo on Feb 15 for 2 people",
    system_prompt="You are a travel assistant. Use tools to help users."
)

print(result["text"])  # AI response in natural language
print(result["tool_calls"])  # List of tools the AI called
```

### Example 3: REST API

MCP tools are also exposed via REST API:

```bash
# List all tools
curl http://localhost:8000/api/mcp/tools

# Search flights
curl -X POST http://localhost:8000/api/mcp/search/flights \
  -H "Content-Type: application/json" \
  -d '{
    "origin": "BKK",
    "destination": "NRT",
    "departure_date": "2025-02-15",
    "adults": 2
  }'

# Geocode location
curl -X POST http://localhost:8000/api/mcp/geocode \
  -H "Content-Type: application/json" \
  -d '{"place_name": "Tokyo Tower"}'
```

## Integration with Agent

The AI Travel Agent can use MCP automatically:

```python
from app.engine.agent import TravelAgent
from app.services.llm_with_mcp import LLMServiceWithMCP
from app.storage.mongodb_storage import MongoStorage

# Create agent with MCP-enabled LLM
storage = MongoStorage()
llm_with_mcp = LLMServiceWithMCP()
agent = TravelAgent(storage, llm_service=llm_with_mcp)

# Agent will use tools automatically when needed
response = await agent.run_turn(
    session_id="user123::trip456",
    user_input="I want to fly from Bangkok to Tokyo on Feb 15"
)

print(response)  # AI response with real flight data
```

## How It Works

```
User Input
    ↓
Gemini LLM (analyzes request)
    ↓
Decides to call: search_flights
    ↓
MCPToolExecutor (executes tool)
    ↓
Amadeus API (returns data)
    ↓
Gemini LLM (formats response)
    ↓
Final Response to User
```

## Testing

### Run Full Test Suite

```bash
cd backend
python test_mcp.py
```

### Run Examples

```bash
cd backend
python examples/mcp_usage_example.py
```

### Test Individual Tools

```python
# In Python REPL or script
import asyncio
from app.services.mcp_server import mcp_executor

async def test():
    result = await mcp_executor.execute_tool(
        "geocode_location",
        {"place_name": "Bangkok"}
    )
    print(result)

asyncio.run(test())
```

## Troubleshooting

### Issue: "No tools loaded"

**Solution**: Check that all imports work:
```bash
cd backend
python -c "from app.services.mcp_server import ALL_MCP_TOOLS; print(len(ALL_MCP_TOOLS))"
```

Should output: `7`

### Issue: "Tool execution failed"

**Solution**: Check API keys:
```bash
# Test Amadeus
curl -X POST https://test.api.amadeus.com/v1/security/oauth2/token \
  -d "grant_type=client_credentials" \
  -d "client_id=YOUR_KEY" \
  -d "client_secret=YOUR_SECRET"

# Test Google Maps
curl "https://maps.googleapis.com/maps/api/geocode/json?address=Bangkok&key=YOUR_KEY"
```

### Issue: "LLM not calling tools"

**Solution**: Ensure you're using `LLMServiceWithMCP`, not regular `LLMService`:
```python
# ✗ Wrong
from app.services.llm import LLMService
llm = LLMService()

# ✓ Correct
from app.services.llm_with_mcp import LLMServiceWithMCP
llm = LLMServiceWithMCP()
```

## Performance Tips

1. **Cache Results**: Google Maps results are cached automatically
2. **Limit Results**: Tools return max 5 options to reduce token usage
3. **Set Max Iterations**: Limit tool calls per turn:
   ```python
   result = await llm.generate_with_tools(
       prompt="...",
       max_tool_calls=3  # Prevent infinite loops
   )
   ```

## Next Steps

- Read full documentation: [`MCP_INTEGRATION.md`](./MCP_INTEGRATION.md)
- See examples: [`examples/mcp_usage_example.py`](../examples/mcp_usage_example.py)
- Check API endpoints: `http://localhost:8000/docs` (FastAPI Swagger UI)

## Support

For issues or questions:
1. Check logs: `backend/data/logs/`
2. Enable debug logging: Set `LOG_LEVEL=DEBUG` in `.env`
3. Test tools individually using REST API

