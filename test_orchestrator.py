import pytest
import os
import dotenv
from project_starter import (
    parse_request,
    init_database,
    ToolCallingAgent,
    OpenAIServerModel,
    inventory_agent,
    quote_agent,
    order_agent,
    financial_agent
)

# Fixture for setting up the test environment
@pytest.fixture(scope="module")
def orchestrator():
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

    # Initialize the orchestrator agent
    agent = ToolCallingAgent(
        model=model,
        tools=[parse_request],
        instructions="You are a helpful agent. You will get quote request from client. "
                     "You have to check inventory status, check previous quote history "
                     "to find appropriate discount, generate quote, process order, "
                     "There are other agents that can help you.",
        managed_agents=[inventory_agent, quote_agent, order_agent, financial_agent]
    )

    return agent

def test_parse_request():
    """Test the parse_request tool directly."""
    request = "I need 100 boxes of Copy Paper for my office by January 15, 2023."
    result = parse_request(request)
    assert hasattr(result, 'request_text')
    assert hasattr(result, 'requested_items')
    # The result should identify Copy Paper as a requested item
    assert any(item.get('item_name') == 'Copy Paper' for item in result.requested_items)

def test_orchestrator_quote_request(orchestrator):
    """Test the orchestrator's ability to handle a quote request."""
    query = "I need a quote for 100 boxes of Copy Paper for delivery on January 15, 2023. (Date of request: 2023-01-01)"
    response = orchestrator.run(query, max_steps=5)

    # Verify the response contains relevant information
    assert response is not None
    assert isinstance(response, str)
    # The response should mention Copy Paper
    assert "Copy Paper" in response
    # The response should include pricing information
    assert "$" in response or "price" in response.lower() or "cost" in response.lower()

def test_orchestrator_order_request(orchestrator):
    """Test the orchestrator's ability to handle an order request."""
    query = "I want to place an order for 20 boxes of Copy Paper today. (Date of request: 2023-01-01)"
    response = orchestrator.run(query, max_steps=5)

    # Verify the response contains relevant information
    assert response is not None
    assert isinstance(response, str)
    # The response should mention the order or processing
    assert "order" in response.lower() or "process" in response.lower()
    # The response should mention Copy Paper
    assert "Copy Paper" in response

def test_orchestrator_inventory_request(orchestrator):
    """Test the orchestrator's ability to handle an inventory request."""
    query = "What is our current inventory status for Copy Paper? (Date of request: 2023-01-01)"
    response = orchestrator.run(query, max_steps=5)

    # Verify the response contains relevant information
    assert response is not None
    assert isinstance(response, str)
    # The response should mention inventory or stock
    assert "inventory" in response.lower() or "stock" in response.lower()
    # The response should mention Copy Paper
    assert "Copy Paper" in response

def test_orchestrator_financial_request(orchestrator):
    """Test the orchestrator's ability to handle a financial request."""
    query = "What is our current financial status? (Date of request: 2023-01-01)"
    response = orchestrator.run(query, max_steps=5)

    # Verify the response contains relevant information
    assert response is not None
    assert isinstance(response, str)
    # The response should mention financial terms
    assert any(term in response.lower() for term in ["financial", "cash", "balance", "asset", "liability"])

# pytest will automatically discover and run the tests
