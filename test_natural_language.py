import pytest
import os
import dotenv
from project_starter import (
    inventory_agent,
    quote_agent,
    order_agent,
    financial_agent,
    orchestrator,
    init_database
)

# Fixture for setting up the test environment
@pytest.fixture(scope="module", autouse=True)
def setup_environment():
    """Set up the test environment once before all tests."""
    # Load environment variables
    dotenv.load_dotenv()

    # Initialize the database
    init_database()

def test_inventory_agent_natural_language():
    """Test the inventory agent with natural language input."""
    # Test checking inventory availability
    query = "Check the current inventory. Do we have enough Copy Paper to send 50 boxes?"
    response = inventory_agent.run(query)

    # Verify the response contains relevant information
    assert response is not None
    assert isinstance(response, str)
    # The response should mention Copy Paper
    assert "Copy Paper" in response
    # The response should indicate whether the item is available
    assert any(term in response.lower() for term in ["available", "stock", "inventory"])

    # Test generating inventory report
    query = "Generate an inventory report for today."
    response = inventory_agent.run(query)

    # Verify the response contains relevant information
    assert response is not None
    assert isinstance(response, str)
    # The response should mention inventory
    assert "inventory" in response.lower()

def test_quote_agent_natural_language():
    """Test the quote agent with natural language input."""
    query = "I need a quote for 100 boxes of Copy Paper and 50 boxes of Premium Paper."
    response = quote_agent.run(query)

    # Verify the response contains relevant information
    assert response is not None
    assert isinstance(response, str)
    # The response should mention the requested items
    assert "Copy Paper" in response
    # The response should include pricing information
    assert "$" in response or "price" in response.lower() or "cost" in response.lower()

def test_order_agent_natural_language():
    """Test the order agent with natural language input."""
    query = "I want to place an order for 20 boxes of Copy Paper."
    response = order_agent.run(query)

    # Verify the response contains relevant information
    assert response is not None
    assert isinstance(response, str)
    # The response should mention the order or processing
    assert "order" in response.lower() or "process" in response.lower()
    # The response should mention Copy Paper
    assert "Copy Paper" in response

def test_financial_agent_natural_language():
    """Test the financial agent with natural language input."""
    query = "What is our current financial status?"
    response = financial_agent.run(query)

    # Verify the response contains relevant information
    assert response is not None
    assert isinstance(response, str)
    # The response should mention financial terms
    assert any(term in response.lower() for term in ["financial", "cash", "balance", "asset", "liability"])

def test_orchestrator_natural_language():
    """Test the orchestrator with natural language input."""
    query = "I need a quote for 100 boxes of Copy Paper, and I want to know if we have enough in stock."
    response = orchestrator.run(query, max_steps=5)

    # Verify the response contains relevant information
    assert response is not None
    assert isinstance(response, str)
    # The response should mention Copy Paper
    assert "Copy Paper" in response
    # The response should mention inventory or stock
    assert "inventory" in response.lower() or "stock" in response.lower()
    # The response should include pricing information
    assert "$" in response or "price" in response.lower() or "cost" in response.lower()

# pytest will automatically discover and run the tests
