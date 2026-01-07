"""
Test script for MCP (Model Context Protocol) integration
Tests both MCP tools and LLM with MCP
"""

import asyncio
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.services.mcp_server import mcp_executor, ALL_MCP_TOOLS
from app.services.llm_with_mcp import LLMServiceWithMCP
from app.core.logging import get_logger

logger = get_logger(__name__)


async def test_mcp_tools():
    """Test MCP tools directly"""
    print("\n" + "="*80)
    print("Testing MCP Tools Directly")
    print("="*80)
    
    # Test 1: Search Flights
    print("\n1. Testing search_flights...")
    result = await mcp_executor.execute_tool(
        tool_name="search_flights",
        parameters={
            "origin": "BKK",
            "destination": "NRT",
            "departure_date": "2025-02-15",
            "adults": 2
        }
    )
    print(f"✓ Result: {result.get('success')}")
    print(f"  Flights found: {result.get('results_count', 0)}")
    if result.get('flights'):
        print(f"  First flight: {result['flights'][0].get('airline')} - {result['flights'][0].get('price', {}).get('total')} {result['flights'][0].get('price', {}).get('currency')}")
    
    # Test 2: Geocode Location
    print("\n2. Testing geocode_location...")
    result = await mcp_executor.execute_tool(
        tool_name="geocode_location",
        parameters={
            "place_name": "Tokyo Tower"
        }
    )
    print(f"✓ Result: {result.get('success')}")
    if result.get('location'):
        print(f"  Coordinates: {result['location'].get('latitude')}, {result['location'].get('longitude')}")
        print(f"  Address: {result['location'].get('formatted_address')}")
    
    # Test 3: Find Nearest Airport
    print("\n3. Testing find_nearest_airport...")
    result = await mcp_executor.execute_tool(
        tool_name="find_nearest_airport",
        parameters={
            "location": "Chiang Mai"
        }
    )
    print(f"✓ Result: {result.get('success')}")
    if result.get('nearest_airport'):
        print(f"  IATA Code: {result['nearest_airport'].get('iata_code')}")
    
    # Test 4: Search Hotels
    print("\n4. Testing search_hotels...")
    result = await mcp_executor.execute_tool(
        tool_name="search_hotels",
        parameters={
            "location": "Tokyo",
            "check_in": "2025-02-15",
            "check_out": "2025-02-17",
            "guests": 2
        }
    )
    print(f"✓ Result: {result.get('success')}")
    print(f"  Hotels found: {result.get('results_count', 0)}")
    if result.get('hotels'):
        print(f"  First hotel: {result['hotels'][0].get('name')} - {result['hotels'][0].get('price', {}).get('total')} {result['hotels'][0].get('price', {}).get('currency')}")


async def test_llm_with_mcp():
    """Test LLM with MCP function calling"""
    print("\n" + "="*80)
    print("Testing LLM with MCP Function Calling")
    print("="*80)
    
    try:
        llm = LLMServiceWithMCP()
        print(f"\n✓ LLM initialized with {len(ALL_MCP_TOOLS)} tools")
        
        # Test 1: Simple flight search
        print("\n1. Testing: 'Find me flights from Bangkok to Tokyo on Feb 15'")
        result = await llm.generate_with_tools(
            prompt="Find me flights from Bangkok to Tokyo on February 15, 2025 for 2 adults",
            system_prompt="You are a helpful travel assistant. Use the available tools to search for travel options. Respond in Thai language.",
            temperature=0.7,
            max_tokens=2000,
            max_tool_calls=5
        )
        
        print(f"\n✓ Response generated")
        print(f"  Tools called: {len(result.get('tool_calls', []))}")
        for i, tool_call in enumerate(result.get('tool_calls', []), 1):
            print(f"    {i}. {tool_call['tool']} - Success: {tool_call['result'].get('success')}")
        print(f"\n  Final response:")
        print(f"  {result.get('text', '')[:300]}...")
        
        # Test 2: Hotel search
        print("\n2. Testing: 'Find hotels in Tokyo for Feb 15-17'")
        result = await llm.generate_with_tools(
            prompt="Find me hotels in Tokyo for February 15-17, 2025 for 2 guests",
            system_prompt="You are a helpful travel assistant. Use the available tools to search for travel options. Respond in Thai language.",
            temperature=0.7,
            max_tokens=2000,
            max_tool_calls=5
        )
        
        print(f"\n✓ Response generated")
        print(f"  Tools called: {len(result.get('tool_calls', []))}")
        for i, tool_call in enumerate(result.get('tool_calls', []), 1):
            print(f"    {i}. {tool_call['tool']} - Success: {tool_call['result'].get('success')}")
        print(f"\n  Final response:")
        print(f"  {result.get('text', '')[:300]}...")
        
    except Exception as e:
        print(f"\n✗ Error: {e}")
        logger.error(f"LLM with MCP test failed: {e}", exc_info=True)


async def main():
    """Run all tests"""
    print("\n" + "="*80)
    print("MCP (Model Context Protocol) Integration Test")
    print("="*80)
    
    try:
        # Test MCP tools directly
        await test_mcp_tools()
        
        # Test LLM with MCP
        await test_llm_with_mcp()
        
        print("\n" + "="*80)
        print("✓ All tests completed!")
        print("="*80)
        
    except Exception as e:
        print(f"\n✗ Test failed: {e}")
        logger.error(f"MCP test failed: {e}", exc_info=True)
    finally:
        # Cleanup
        await mcp_executor.close()


if __name__ == "__main__":
    asyncio.run(main())

