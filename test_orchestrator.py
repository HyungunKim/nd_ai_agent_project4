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
    agent = ToolCallingAgent(model=model,
                         tools=[parse_request],
                         instructions="You are a helpful agent. You will get quote request from client. "
                                      "You have to check inventory status, check previous quote history "
                                      "to find appropriate discount, generate quote, process order, "
                                      "There are other agents that can help you."
                                      "Think step by step. Call one necessary tools or agents for that step."
                                      "When querying to other agents please provide the (Date of request) in the request text."
                                     "Also a boiler plate input of 'additional_args': {} is required to call other agents."
                                     "For example: "
                     "{'task': '(Date of request: 2025-08-01) I want to check the inventory status of A4 paper.', 'additional_args': {}}",
                         managed_agents=[inventory_agent, quote_agent, order_agent, financial_agent],
                         max_tool_threads=1)


    return agent

def test_parse_request():
    """Test the parse_request tool directly."""
    request = "I need 100 boxes of A4 paper for my office by September 15, 2025."
    result = parse_request(request)
    print(result)
    assert hasattr(result, 'request_text')
    assert hasattr(result, 'requested_items')
    # The result should identify Copy Paper as a requested item
    assert any(item.get('item_name') == 'A4 paper' for item in result.requested_items)

def test_orchestrator_quote_request(orchestrator):
    """Test the orchestrator's ability to handle a quote request."""
    query = "I need a quote for 100 A4 paper for delivery on September 15, 2025. (Date of request: 2025-08-01)"
    response = orchestrator.run(query, max_steps=5)

    # Verify the response contains relevant information
    assert response is not None
    assert isinstance(response, str)
    # The response should mention Copy Paper
    assert "A4 paper" in response
    # The response should include pricing information
    assert "$" in response or "price" in response.lower() or "cost" in response.lower()

def test_orchestrator_order_request(orchestrator):
    """Test the orchestrator's ability to handle an order request."""
    query = "I want to place an order for 20 A4 paper today. (Date of request: 2025-08-01)"
    response = orchestrator.run(query)

    # Verify the response contains relevant information
    assert response is not None
    assert isinstance(response, str)
    # The response should mention the order or processing
    assert "order" in response.lower() or "process" in response.lower()
    # The response should mention Copy Paper
    assert "A4 paper" in response

def test_orchestrator_inventory_request(orchestrator):
    """Test the orchestrator's ability to handle an inventory request."""
    query = "What is our current inventory status for A4 paper? (Date of request: 2025-08-01)"
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
    query = "What is our current financial status? (Date of request: 2025-08-01)"
    response = orchestrator.run(query, max_steps=5)

    # Verify the response contains relevant information
    assert response is not None
    assert isinstance(response, str)
    # The response should mention financial terms
    assert any(term in response.lower() for term in ["financial", "cash", "balance", "asset", "liability"])

# pytest will automatically discover and run the tests
