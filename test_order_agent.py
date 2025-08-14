import pytest
import os
import dotenv
from project_starter import (
    Order,
    OrderStatus,
    process_order,
    check_order_status,
    get_supplier_delivery_date,
    get_available_paper_supplies,
    init_database,
    ToolCallingAgent,
    OpenAIServerModel,
    OrderItem
)

# Fixture for setting up the test environment
@pytest.fixture(scope="module")
def order_agent():
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

    # Initialize the order agent
    agent = ToolCallingAgent(
        model=model,
        tools=[process_order, check_order_status, get_supplier_delivery_date, get_available_paper_supplies],
        name="OrderAgent",
        instructions="""
        You are a helpful agent. You will get order request from client. You can process order, check order status, get supplier delivery date.
        When using 'process_order' tool look at this example to provide arguments arguments: {'order_date': '2025-08-01', 'items': [{'item_name': 'A4 paper', 'quantity': 20, 'price': 1}]
        Here the 'price' is total price for that item and quantity.
        Always use the exact item names from the paper_supplies list. You can use the get_available_paper_supplies tool 
        to get a list of all available paper supply item names. This ensures that the correct items are identified and processed.
        For example, 'Glossy paper' instead of 'glossy paper'. 
        Use this format for input of tools and output of your responses
        """,
        description="""
        The agent for processing orders. It has access to tools such as process_order, check_order_status, get_supplier_delivery_date.
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

def test_get_supplier_delivery_date():
    """Test the get_supplier_delivery_date tool directly."""
    result = get_supplier_delivery_date("2025-08-01", 100)
    print(result)
    assert isinstance(result, str)
    # The result should be a date string
    assert "-" in result  # Simple check for date format

def test_process_order():
    """Test the process_order tool directly."""
    # Create a simple order with one item
    items = [OrderItem(item_name="A4 paper", quantity=10, price=0.5)]
    result = process_order(items, "2025-08-01")
    print()
    print(result)
    assert isinstance(result, Order)
    assert hasattr(result, 'order_results')
    assert hasattr(result, 'total_sales_amount')
    assert hasattr(result, 'restock_results')

    # Test with an item that doesn't exist in paper_supplies
    items = [OrderItem(item_name="Nonexistent Item", quantity=10, price=0.5)]
    result = process_order(items, "2025-08-01")
    print()
    print(result)
    assert isinstance(result, Order)
    assert len(result.order_results) == 1
    assert "Invalid item name" in result.order_results[0].status

def test_check_order_status():
    """Test the check_order_status tool directly."""
    # First create an order to get an order ID
    init_database()
    items = [OrderItem(item_name="A4 paper", quantity=100, price=5.0)]
    order = process_order(items, "2025-08-01")
    # Get the transaction ID from the first order result
    if order.order_results and len(order.order_results) > 0:
        transaction_id = order.order_results[0].transaction_id
        if transaction_id:
            result = check_order_status(transaction_id, "2025-08-02")
            print(result)
            assert isinstance(result, OrderStatus)



def test_order_agent_process_order(order_agent):
    """Test the order agent's ability to process an order."""
    query = "I want to place an order for 20 boxes of A4 paper today. The price is 1$ in total. (Date of request: 2025-08-01)"
    response = order_agent.run(query)

    # Verify the response contains relevant information
    assert response is not None
    assert isinstance(response, str)
    # The response should mention the order or processing
    assert "order" in response.lower() or "process" in response.lower()
    # The response should mention Copy Paper
    assert "A4 paper" in response

def test_order_agent_check_status(order_agent):
    """Test the order agent's ability to check an order status."""
    # First create an order to get an order ID
    items = [OrderItem(item_name="A4 paper", quantity=10)]
    order = process_order(items, "2025-08-01")
    print(order)
    # Get the transaction ID from the first order result
    if order.order_results and len(order.order_results) > 0:
        transaction_id = order.order_results[0].transaction_id
        if transaction_id:
            query = f"What is the status of order {transaction_id}? (Date of request: 2025-08-01)"
            response = order_agent.run(query)
            print()
            print(response)
            # Verify the response contains relevant information
            assert response is not None
            assert isinstance(response, str)
            # The response should mention the order or status
            assert "order" in response.lower() or "status" in response.lower()
            # The response should include the order ID
            assert str(transaction_id) in response

def test_order_agent_exact_item_names(order_agent):
    """Test the order agent's ability to use exact item names from paper_supplies."""
    query = "I want to place an order for 20 sheets of glossy paper today. The price is 4$ in total. (Date of request: 2025-08-01)"
    response = order_agent.run(query)

    # Verify the response contains the exact item name from paper_supplies
    assert response is not None
    assert isinstance(response, str)
    # The response should use the exact item name "Glossy paper" instead of just "glossy paper"
    assert "Glossy paper" in response

# pytest will automatically discover and run the tests
