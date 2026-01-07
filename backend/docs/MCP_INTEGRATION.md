# Model Context Protocol (MCP) Integration

## Overview

The AI Travel Agent now supports **Model Context Protocol (MCP)**, enabling Gemini LLM to directly call external APIs through function calling. This allows the AI to:

1. Search for flights, hotels, transfers, and activities via Amadeus API
2. Geocode locations and find airports via Google Maps API
3. Make intelligent decisions about when to call which API

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      Gemini LLM (with MCP)                  │
│  - Decides when to call tools                               │
│  - Formats parameters                                       │
│  - Interprets results                                       │
└────────────────────────┬────────────────────────────────────┘
                         │
                         │ Function Calls
                         │
┌────────────────────────▼────────────────────────────────────┐
│                   MCPToolExecutor                           │
│  - Executes tool requests                                   │
│  - Routes to appropriate service                            │
│  - Formats results for LLM                                  │
└────────────────────────┬────────────────────────────────────┘
                         │
         ┌───────────────┴───────────────┐
         │                               │
┌────────▼────────┐            ┌────────▼────────┐
│  Amadeus API    │            │ Google Maps API │
│  - Flights      │            │  - Geocoding    │
│  - Hotels       │            │  - IATA Lookup  │
│  - Transfers    │            │  - Place Details│
│  - Activities   │            └─────────────────┘
└─────────────────┘
```

## Available Tools

### Amadeus Tools

#### 1. `search_flights`
Search for flight offers.

**Parameters:**
- `origin` (string, required): Origin airport IATA code or city name
- `destination` (string, required): Destination airport IATA code or city name
- `departure_date` (string, required): Date in YYYY-MM-DD format
- `adults` (integer, optional): Number of passengers (default: 1)
- `return_date` (string, optional): Return date for round-trip

**Example:**
```json
{
  "origin": "Bangkok",
  "destination": "Tokyo",
  "departure_date": "2025-02-15",
  "adults": 2
}
```

#### 2. `search_hotels`
Search for hotel offers.

**Parameters:**
- `location` (string, required): City name or IATA code
- `check_in` (string, required): Check-in date in YYYY-MM-DD format
- `check_out` (string, required): Check-out date in YYYY-MM-DD format
- `guests` (integer, optional): Number of guests (default: 1)

#### 3. `search_transfers`
Search for ground transfer options.

**Parameters:**
- `origin` (string, required): Origin location (airport code or address)
- `destination` (string, required): Destination address
- `date` (string, required): Transfer date in YYYY-MM-DD format
- `passengers` (integer, optional): Number of passengers (default: 1)

#### 4. `search_activities`
Search for tours and activities.

**Parameters:**
- `location` (string, required): City name or location
- `radius` (integer, optional): Search radius in km (default: 10)

### Google Maps Tools

#### 5. `geocode_location`
Convert place name to coordinates.

**Parameters:**
- `place_name` (string, required): Place name, address, or landmark

#### 6. `find_nearest_airport`
Find nearest airport IATA code.

**Parameters:**
- `location` (string, required): City name or place

#### 7. `get_place_details`
Get detailed information about a place.

**Parameters:**
- `place_name` (string, required): Place name or business name

## Usage

### Basic Usage

```python
from app.services.llm_with_mcp import LLMServiceWithMCP

# Initialize LLM with MCP
llm = LLMServiceWithMCP()

# Generate response with tool calling
result = await llm.generate_with_tools(
    prompt="Find me flights from Bangkok to Tokyo on Feb 15 for 2 adults",
    system_prompt="You are a travel assistant. Use tools to help users.",
    temperature=0.7,
    max_tokens=2000,
    max_tool_calls=5
)

print(result["text"])  # Final response
print(result["tool_calls"])  # List of tools called
```

### Integration with Agent

```python
from app.engine.agent import TravelAgent
from app.services.llm_with_mcp import LLMServiceWithMCP

# Create agent with MCP-enabled LLM
llm_with_mcp = LLMServiceWithMCP()
agent = TravelAgent(storage, llm_service=llm_with_mcp)

# Agent will automatically use tools when needed
response = await agent.run_turn(
    session_id="user123::trip456",
    user_input="I want to fly from Chiang Mai to Osaka on January 20"
)
```

## How It Works

1. **User Input**: User asks for travel information
2. **LLM Analysis**: Gemini analyzes the request and decides which tools to call
3. **Tool Execution**: MCPToolExecutor executes the requested tools
4. **Result Processing**: Results are formatted and sent back to LLM
5. **Final Response**: LLM generates a natural language response using tool results

### Example Flow

```
User: "Find me flights from Bangkok to Tokyo on Feb 15"
  ↓
Gemini: "I need to search flights"
  ↓
Tool Call: search_flights(origin="Bangkok", destination="Tokyo", departure_date="2025-02-15")
  ↓
Amadeus API: Returns flight offers
  ↓
Tool Result: {"success": true, "flights": [...]}
  ↓
Gemini: "พบเที่ยวบิน 5 เที่ยวจากกรุงเทพไปโตเกียว..."
```

## Configuration

### Environment Variables

```bash
# Gemini API (required)
GEMINI_API_KEY=your_gemini_api_key
GEMINI_MODEL_NAME=gemini-1.5-flash

# Amadeus API (required for flight/hotel tools)
AMADEUS_API_KEY=your_amadeus_key
AMADEUS_API_SECRET=your_amadeus_secret
AMADEUS_ENV=test  # or "production"

# Google Maps API (required for geocoding tools)
GOOGLE_MAPS_API_KEY=your_google_maps_key
```

### Timeout Settings

```python
# In app/core/config.py
gemini_timeout_seconds = 60  # Max time for LLM call
gemini_max_retries = 3  # Retry attempts
```

## Error Handling

The MCP system handles errors gracefully:

1. **Tool Execution Errors**: If a tool fails, it returns an error object to the LLM
2. **LLM Timeout**: If LLM takes too long, a timeout error is raised
3. **Max Iterations**: Limited to 5 tool calls per turn to prevent infinite loops

### Example Error Response

```json
{
  "success": false,
  "tool": "search_flights",
  "error": "Could not resolve IATA code for 'InvalidCity'"
}
```

## Performance Optimization

1. **Caching**: Google Maps results are cached in memory
2. **Parallel Calls**: Multiple tools can be called in parallel (future enhancement)
3. **Result Limiting**: Only top 5 results returned per tool to reduce token usage

## Testing

### Test MCP Tools Directly

```python
from app.services.mcp_server import mcp_executor

# Test flight search
result = await mcp_executor.execute_tool(
    tool_name="search_flights",
    parameters={
        "origin": "BKK",
        "destination": "NRT",
        "departure_date": "2025-02-15",
        "adults": 2
    }
)

print(result)
```

### Test LLM with MCP

```python
from app.services.llm_with_mcp import LLMServiceWithMCP

llm = LLMServiceWithMCP()

result = await llm.generate_with_tools(
    prompt="Find hotels in Tokyo for Feb 15-17",
    system_prompt="You are a helpful travel assistant."
)

print(result["text"])
print(f"Tools called: {len(result['tool_calls'])}")
```

## Monitoring

Tool calls are logged with full details:

```
INFO - Executing MCP tool: search_flights with params: {'origin': 'BKK', 'destination': 'NRT', ...}
INFO - LLM requested tool: search_flights
INFO - MCP iteration 1/5
```

Check logs in `backend/data/logs/` for detailed execution traces.

## Future Enhancements

1. **Parallel Tool Calls**: Execute multiple tools simultaneously
2. **Tool Chaining**: Automatic chaining of related tools (e.g., geocode → find_airport → search_flights)
3. **Custom Tools**: Easy addition of new tools via plugin system
4. **Tool Analytics**: Track which tools are most used and their success rates
5. **Streaming Results**: Stream tool results as they become available

## Troubleshooting

### Issue: LLM not calling tools

**Solution**: Check that tools are properly initialized:
```python
llm = LLMServiceWithMCP()
print(f"Tools loaded: {len(llm.tools)}")  # Should be > 0
```

### Issue: Tool execution fails

**Solution**: Check API keys and credentials:
```bash
# Test Amadeus
curl -X POST https://test.api.amadeus.com/v1/security/oauth2/token \
  -d "grant_type=client_credentials&client_id=YOUR_KEY&client_secret=YOUR_SECRET"

# Test Google Maps
curl "https://maps.googleapis.com/maps/api/geocode/json?address=Bangkok&key=YOUR_KEY"
```

### Issue: Timeout errors

**Solution**: Increase timeout in config:
```python
# app/core/config.py
gemini_timeout_seconds = 120  # Increase to 2 minutes
```

## References

- [Gemini Function Calling Documentation](https://ai.google.dev/docs/function_calling)
- [Amadeus API Documentation](https://developers.amadeus.com/)
- [Google Maps API Documentation](https://developers.google.com/maps)

