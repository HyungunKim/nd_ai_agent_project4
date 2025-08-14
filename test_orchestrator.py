import pytest
import os
import dotenv
from project_starter import (
    parse_request,
    get_available_paper_supplies,
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
                         tools=[parse_request, get_available_paper_supplies],
                         instructions="You are a helpful agent. You will get quote request from client. "
                                      "You have to check inventory status, check previous quote history "
                                      "to find appropriate discount, generate quote, process order, "
                                      "There are other agents that can help you."
                                      "Think step by step. Call one necessary tools or agents for that step."
                                      "When querying to other agents please provide the (Date of request) in the request text."
                                      "Convert user request items to exact item names from paper_supplies list."
                                      "That is if user request is '100 copy paper' then convert it to 'Standard copy paper' which is in paper_supplies."
                                      "Always use the exact item names from the paper_supplies list. You can use the get_available_paper_supplies tool "
                                      "to get a list of all available paper supply item names. This ensures that the correct items are identified and processed."
                                      "For example, 'Glossy paper' instead of 'glossy paper'. "
                                      "Use this format for input of tools and output of your responses"
                                      "Also a boiler plate input of 'additional_args': {} is required to call other agents."
                                      "For example: "
                     "{'task': '(Date of request: 2025-08-01) I want to check the inventory status of A4 paper.', 'additional_args': {}}",
                         managed_agents=[inventory_agent, quote_agent, order_agent, financial_agent],
                         max_tool_threads=1)


    return agent

def test_get_available_paper_supplies():
    """Test the get_available_paper_supplies tool directly."""
    result = get_available_paper_supplies()
    print(result)
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
    init_database()
    query = "I need a quote for 100 a4 glossy paper for delivery on September 15, 2025. (Date of request: 2025-08-01)"
    response = orchestrator.run(query)

    # Verify the response contains relevant information
    assert response is not None
    assert isinstance(response, str)
    # The response should mention Copy Paper
    assert "A4 glossy paper" in response
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

def test_orchestrator_exact_item_names(orchestrator):
    """Test the orchestrator's ability to use exact item names from paper_supplies."""
    query = "I need a quote for 100 sheets of glossy paper for delivery on September 15, 2025. (Date of request: 2025-08-01)"
    response = orchestrator.run(query)

    # Verify the response contains the exact item name from paper_supplies
    assert response is not None
    assert isinstance(response, str)
    # The response should use the exact item name "Glossy paper" instead of just "glossy paper"
    assert "Glossy paper" in response

    query = "I need a quote for 100 sheets of bright color papers for delivery on September 15, 2025. (Date of request: 2025-08-01)"
    response = orchestrator.run(query)

    # Verify the response contains the exact item name from paper_supplies
    assert response is not None
    assert isinstance(response, str)
    # The response should use the exact item name "Glossy paper" instead of just "glossy paper"
    assert "Bright-colored paper" in response

# pytest will automatically discover and run the tests
