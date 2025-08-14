import pytest
import os
import dotenv
from project_starter import (
    InventoryStatus,
    InventoryReport,
    RestockReport,
    check_inventory_status,
    get_inventory_report,
    restock_inventory,
    get_available_paper_supplies,
    init_database,
    ToolCallingAgent,
    CodeAgent,
    OpenAIServerModel, create_transaction
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
    agent = ToolCallingAgent(
        model=model,
        tools=[check_inventory_status, get_inventory_report, restock_inventory, get_available_paper_supplies],
        name="InventoryAgent",
        instructions="Always use the exact item names from the paper_supplies list. You can use the get_available_paper_supplies tool"
                     "to get a list of all available paper supply item names. This ensures that the correct items are identified and processed."
                     "For example, 'Glossy paper' instead of 'glossy paper'. "
                     "Use this format for input of tools and output of your responses",
        description="""
        The agent for handling inventory logic. It has access to tools such as check_inventory_status, get_inventory_report, and restock_inventory.
        """
    )

    return agent

def test_get_available_paper_supplies():
    """Test the get_available_paper_supplies tool directly."""
    result = get_available_paper_supplies()
    assert isinstance(result, list)
    assert len(result) > 0
    # Check for some specific paper items that should be in the list
    assert "A4 paper" in result
    assert "A4 glossy paper" in result
    assert "Cardstock" in result
    # Check for newly added items
    assert "Poster board" in result
    assert "Adhesive tape" in result
    assert "Decorative masking tape" in result
    assert "Biodegradable packaging tape" in result
    assert "A3 drawing paper" in result
    assert "Balloons" in result

def test_check_inventory_status():
    """Test the check_inventory_status tool directly."""
    # Test with an item that should exist
    result = check_inventory_status("Standard copy paper", 100, "2025-08-01")
    print(result)
    assert isinstance(result, InventoryStatus)
    assert hasattr(result, 'item_name')
    assert hasattr(result, 'available')
    assert hasattr(result, 'current_stock')

    # Test with an item that doesn't exist in inventory but is in paper_supplies
    result = check_inventory_status("Biodegradable banner paper", 10, "2025-08-01")
    assert isinstance(result, InventoryStatus)
    assert not result.available
    assert "Item not found in inventory" in result.status

    # Test with an item that doesn't exist in paper_supplies
    result = check_inventory_status("Nonexistent Item", 10, "2025-08-01")
    assert isinstance(result, InventoryStatus)
    assert not result.available
    assert "Invalid item name" in result.status

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
    print(response)
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

    query = "Check if we have 100 Copy paper available as of August 1, 2025."
    response = inventory_agent.run(query)

    # Verify the response contains relevant information
    assert response is not None
    assert isinstance(response, str)
    assert "Standard copy paper" in response

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

    query = ("What inventory items should we stock up for next month? (Date of request: 2025-08-01)."
             "Expect 300 stocks are sold for each item this month.")
    response = inventory_agent.run(query)
    assert response is not None

def test_restock_inventory():
    """Test the restock_inventory tool directly."""
    init_database()
    create_transaction(
        item_name="A4 paper",
        transaction_type="sales",
        quantity = 700,
        price = 50,
        date = "2025-07-31"
    )
    create_transaction(
        item_name="Letter-sized paper",
        transaction_type="sales",
        quantity=700,
        price=50,
        date="2025-07-31"
    )
    create_transaction(
        item_name="Cardstockr",
        transaction_type="sales",
        quantity=800,
        price=50,
        date="2025-07-31"
    )
    # Get the inventory report before restocking
    before_report = get_inventory_report("2025-08-01")

    # Restock inventory
    result = restock_inventory("2025-08-01")
    print()
    print(result)
    # Verify the result is a RestockReport
    assert isinstance(result, RestockReport)
    assert hasattr(result, 'restocked_items')
    assert hasattr(result, 'total_items_restocked')
    assert hasattr(result, 'total_restock_cost')

    # Verify that items were restocked
    assert result.total_items_restocked >= 0

    # Verify that the total restock cost is positive
    assert result.total_restock_cost >= 0

    # Verify that each restocked item has the correct attributes
    for item in result.restocked_items:
        assert hasattr(item, 'item_name')
        assert hasattr(item, 'quantity')
        assert hasattr(item, 'price')
        assert hasattr(item, 'status')
        assert hasattr(item, 'delivery_date')
        assert hasattr(item, 'transaction_id')

def test_inventory_agent_restock(inventory_agent):
    """Test the inventory agent's ability to restock inventory."""

    create_transaction(
        item_name="A4 paper",
        transaction_type="sales",
        quantity=700,
        price=50,
        date="2025-07-31"
    )
    create_transaction(
        item_name="Letter-sized paper",
        transaction_type="sales",
        quantity=700,
        price=50,
        date="2025-07-31"
    )
    create_transaction(
        item_name="Cardstockr",
        transaction_type="sales",
        quantity=800,
        price=50,
        date="2025-07-31"
    )
    query = "Restock all inventory items that are below their minimum stock levels as of August 1, 2025."
    response = inventory_agent.run(query)

    # Verify the response contains relevant information
    assert response is not None
    assert isinstance(response, str)
    # The response should mention restocking
    assert "restock" in response.lower() or "restocked" in response.lower()

def test_inventory_agent_exact_item_names(inventory_agent):
    """Test the inventory agent's ability to use exact item names from paper_supplies."""
    query = "Check if we have 50 photo papers available as of August 1, 2025."
    response = inventory_agent.run(query)

    # Verify the response contains the exact item name from paper_supplies
    assert response is not None
    assert isinstance(response, str)
    # The response should use the exact item name "Glossy paper" instead of just "glossy paper"
    assert "Photo papers" in response

# pytest will automatically discover and run the tests
