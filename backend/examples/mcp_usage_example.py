"""
Example: Using MCP (Model Context Protocol) with AI Travel Agent
Demonstrates how to use MCP tools and LLM with function calling
"""

import asyncio
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.llm_with_mcp import LLMServiceWithMCP
from app.services.mcp_server import mcp_executor


async def example_1_direct_tool_call():
    """
    Example 1: Call MCP tools directly
    Useful for testing or when you know exactly which tool to use
    """
    print("\n" + "="*80)
    print("Example 1: Direct Tool Call")
    print("="*80)
    
    # Search for flights
    print("\n📍 Searching for flights from Bangkok to Tokyo...")
    result = await mcp_executor.execute_tool(
        tool_name="search_flights",
        parameters={
            "origin": "Bangkok",
            "destination": "Tokyo",
            "departure_date": "2025-02-15",
            "adults": 2
        }
    )
    
    if result["success"]:
        print(f"✓ Found {result['results_count']} flights")
        for i, flight in enumerate(result["flights"][:3], 1):
            print(f"\n  Flight {i}:")
            print(f"    Airline: {flight['airline']}")
            print(f"    Route: {flight['departure']['airport']} → {flight['arrival']['airport']}")
            print(f"    Price: {flight['price']['total']} {flight['price']['currency']}")
    else:
        print(f"✗ Error: {result.get('error')}")


async def example_2_llm_with_tools():
    """
    Example 2: Let LLM decide which tools to use
    The AI will automatically call the right tools based on user input
    """
    print("\n" + "="*80)
    print("Example 2: LLM with Automatic Tool Selection")
    print("="*80)
    
    llm = LLMServiceWithMCP()
    
    # User asks for flights
    print("\n💬 User: 'I want to fly from Chiang Mai to Osaka on January 20 for 3 people'")
    result = await llm.generate_with_tools(
        prompt="I want to fly from Chiang Mai to Osaka on January 20, 2025 for 3 people. Please find me some options.",
        system_prompt="You are a helpful travel assistant. Use the available tools to search for travel options. Respond in Thai language with detailed information.",
        temperature=0.7,
        max_tokens=2000
    )
    
    print(f"\n🤖 AI Response:")
    print(f"{result['text']}")
    
    print(f"\n📊 Tools Used:")
    for i, tool_call in enumerate(result['tool_calls'], 1):
        print(f"  {i}. {tool_call['tool']}")
        print(f"     Parameters: {tool_call['parameters']}")
        print(f"     Success: {tool_call['result']['success']}")


async def example_3_multi_step_planning():
    """
    Example 3: Complex multi-step travel planning
    LLM calls multiple tools in sequence to plan a complete trip
    """
    print("\n" + "="*80)
    print("Example 3: Multi-Step Travel Planning")
    print("="*80)
    
    llm = LLMServiceWithMCP()
    
    # User asks for complete trip planning
    print("\n💬 User: 'Plan a 3-day trip to Tokyo from Feb 15-17, including flights and hotels'")
    result = await llm.generate_with_tools(
        prompt="""Plan a complete 3-day trip to Tokyo for me:
        - Departure from Bangkok on February 15, 2025
        - Return on February 17, 2025
        - 2 adults
        - Need both flights and hotel recommendations
        
        Please search for options and give me a summary.""",
        system_prompt="You are an expert travel planner. Use all available tools to create a comprehensive travel plan. Respond in Thai language.",
        temperature=0.7,
        max_tokens=3000,
        max_tool_calls=10  # Allow more tool calls for complex planning
    )
    
    print(f"\n🤖 AI Travel Plan:")
    print(f"{result['text']}")
    
    print(f"\n📊 Planning Steps (Tools Used):")
    for i, tool_call in enumerate(result['tool_calls'], 1):
        print(f"  Step {i}: {tool_call['tool']}")
        if tool_call['result']['success']:
            results_count = tool_call['result'].get('results_count', 0)
            print(f"          → Found {results_count} options")
        else:
            print(f"          → Error: {tool_call['result'].get('error')}")


async def example_4_geocoding_and_location():
    """
    Example 4: Using Google Maps tools for location services
    """
    print("\n" + "="*80)
    print("Example 4: Location Services with Google Maps")
    print("="*80)
    
    # Find coordinates
    print("\n📍 Finding coordinates for 'Tokyo Tower'...")
    result = await mcp_executor.execute_tool(
        tool_name="geocode_location",
        parameters={"place_name": "Tokyo Tower"}
    )
    
    if result["success"]:
        loc = result["location"]
        print(f"✓ Location found:")
        print(f"  Address: {loc['formatted_address']}")
        print(f"  Coordinates: {loc['latitude']}, {loc['longitude']}")
    
    # Find nearest airport
    print("\n✈️ Finding nearest airport to 'Phuket'...")
    result = await mcp_executor.execute_tool(
        tool_name="find_nearest_airport",
        parameters={"location": "Phuket"}
    )
    
    if result["success"]:
        airport = result["nearest_airport"]
        print(f"✓ Nearest airport: {airport['iata_code']}")
        print(f"  Coordinates: {airport['coordinates']['latitude']}, {airport['coordinates']['longitude']}")


async def example_5_error_handling():
    """
    Example 5: How MCP handles errors gracefully
    """
    print("\n" + "="*80)
    print("Example 5: Error Handling")
    print("="*80)
    
    # Try to search with invalid parameters
    print("\n🔍 Attempting search with invalid location...")
    result = await mcp_executor.execute_tool(
        tool_name="geocode_location",
        parameters={"place_name": "NonExistentPlace12345XYZ"}
    )
    
    if not result["success"]:
        print(f"✓ Error handled gracefully:")
        print(f"  Error: {result['error']}")
        print(f"  Tool: {result['tool']}")
    
    # LLM will also handle errors gracefully
    print("\n💬 LLM handling invalid request...")
    llm = LLMServiceWithMCP()
    result = await llm.generate_with_tools(
        prompt="Find me flights from InvalidCity to AnotherInvalidCity",
        system_prompt="You are a travel assistant. If tools fail, explain the issue politely in Thai.",
        temperature=0.7
    )
    
    print(f"\n🤖 AI Response:")
    print(f"{result['text']}")


async def example_6_coordinate_transfer():
    """
    Example 6: Multi-step transfer search using coordinates
    1. Geocode start location (Siam Paragon)
    2. Geocode end location (Suvarnabhumi Airport)
    3. Search transfers using coordinates
    """
    print("\n" + "="*80)
    print("Example 6: Coordinate-based Transfer Search")
    print("="*80)
    
    llm = LLMServiceWithMCP()
    
    prompt = """
    I need a transfer from Siam Paragon to Suvarnabhumi Airport tomorrow at 10:00 AM.
    Please find the exact coordinates for both places first, then search for a transfer using those coordinates.
    Tell me the available options and prices.
    """
    
    print(f"\n💬 User: '{prompt.strip()}'")
    
    result = await llm.generate_with_tools(
        prompt=prompt,
        system_prompt="You are a smart travel assistant. For transfers, always find exact coordinates of start and end points using geocoding before searching for transfers to ensure accuracy.",
        temperature=0.5,
        max_tool_calls=5  # Need multiple steps
    )
    
    print(f"\n🤖 AI Response:")
    print(f"{result['text']}")
    
    print(f"\n📊 Steps Taken:")
    for i, tool_call in enumerate(result['tool_calls'], 1):
        print(f"  Step {i}: {tool_call['tool']}")
        if tool_call['tool'] == 'geocode_location':
            loc = tool_call['result'].get('location', {})
            print(f"          → Found: {loc.get('place_name')} ({loc.get('latitude')}, {loc.get('longitude')})")
        elif tool_call['tool'] == 'search_transfers_by_geo':
            count = tool_call['result'].get('results_count', 0)
            print(f"          → Found {count} transfer options")


async def main():
    """Run all examples"""
    print("\n" + "="*80)
    print("MCP (Model Context Protocol) Usage Examples")
    print("AI Travel Agent with Amadeus & Google Maps Integration")
    print("="*80)
    
    try:
        # Run examples
        # await example_1_direct_tool_call()
        # await example_2_llm_with_tools()
        # await example_3_multi_step_planning()
        # await example_4_geocoding_and_location()
        # await example_5_error_handling()
        await example_6_coordinate_transfer()
        
        print("\n" + "="*80)
        print("✓ All examples completed!")
        print("="*80)

        
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # Cleanup
        await mcp_executor.close()


if __name__ == "__main__":
    # Run examples
    asyncio.run(main())

