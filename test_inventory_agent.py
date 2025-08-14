import pytest
import os
import dotenv
from project_starter import (
    InventoryStatus,
    InventoryReport,
    check_inventory_status,
    get_inventory_report,
    init_database,
    ToolCallingAgent,
    CodeAgent,
    OpenAIServerModel
)

# Fixture for setting up the test environment
@pytest.fixture(scope="module")
def inventory_agent():
    """Set up the test environment once before all tests."""
    # Load environment variables
    dotenv.load_dotenv()
    openai_api_key = os.getenv("UDACITY_OPENAI_API_KEY")

    # Initialize the model
    model = OpenAIServerModel(
        model_id="gpt-4o-mini",
        api_base="https://openai.vocareum.com/v1",
        api_key=openai_api_key,
    )

    # Initialize the database
    init_database()

    # Initialize the inventory agent
    agent = CodeAgent(
        model=model,
        tools=[check_inventory_status, get_inventory_report],
        name="InventoryAgent",
        description="""
        The agent for handling inventory logic. It has access to tools such as check_inventory_status and get_inventory_report.
        """
    )

    return agent

def test_check_inventory_status():
    """Test the check_inventory_status tool directly."""
    # Test with an item that should exist
    result = check_inventory_status("Copy Paper", 100, "2025-08-01")
    assert isinstance(result, InventoryStatus)
    assert hasattr(result, 'item_name')
    assert hasattr(result, 'available')
    assert hasattr(result, 'current_stock')

    # Test with an item that doesn't exist
    result = check_inventory_status("Nonexistent Item", 10, "2025-08-01")
    assert isinstance(result, InventoryStatus)
    assert not result.available
    assert result.status == "Insufficient stock"

def test_get_inventory_report():
    """Test the get_inventory_report tool directly."""
    result = get_inventory_report("2025-08-01")
    assert isinstance(result, InventoryReport)
    assert hasattr(result, 'total_items')
    assert hasattr(result, 'items_in_stock')
    assert hasattr(result, 'inventory_value')

def test_inventory_agent_check_status(inventory_agent):
    """Test the inventory agent's ability to check inventory status."""
    query = "Check if we have 50 Letter-sized paper available as of August 1, 2025."
    response = inventory_agent.run(query)

    # Verify the response contains relevant information
    assert response is not None
    assert isinstance(response, str)
    # The response should mention Copy Paper
    assert "Letter-sized paper" in response

    query = "Check if we have 100 A4 paper available as of August 1, 2025."
    response = inventory_agent.run(query)

    # Verify the response contains relevant information
    assert response is not None
    assert isinstance(response, str)
    assert "A4 paper" in response

    query = "Check if we have 100 Cardstock available as of August 1, 2025."
    response = inventory_agent.run(query)

    # Verify the response contains relevant information
    assert response is not None
    assert isinstance(response, str)
    assert "Cardstock" in response

def test_inventory_agent_get_report(inventory_agent):
    """Test the inventory agent's ability to generate an inventory report."""
    query = "Generate an inventory report as of August 1, 2025."
    response = inventory_agent.run(query)

    # Verify the response contains relevant information
    assert response is not None
    assert isinstance(response, str)
    # The response should mention inventory value
    assert "inventory value" in response.lower() or "inventory report" in response.lower()

def test_inventory_agent_get_report(inventory_agent):
    """Test the inventory agent's ability to generate an inventory report."""
    query = ("What inventory items should we stock up for next month? (Date of request: 2025-08-01).")
    response = inventory_agent.run(query)

    # Verify the response contains relevant information
    assert response is not None
    #
    query = ("What inventory items should we stock up for next month? (Date of request: 2025-08-01)."
             "Expect 300 stocks are sold for each item this month.")
    response = inventory_agent.run(query)
    # query = "What inventory items should we stock up for next month? We have (Date of request: 2025-08-01)"
    # response = inventory_agent.run(query)
# pytest will automatically discover and run the tests
