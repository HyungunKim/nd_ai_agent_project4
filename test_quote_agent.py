import pytest
import os
import dotenv
from project_starter import (
    Quote,
    BulkDiscountInfo,
    # generate_quote,
    calculate_bulk_discount,
    search_quote_history,
    get_available_paper_supplies,
    init_database,
    ToolCallingAgent,
    OpenAIServerModel
)

# Fixture for setting up the test environment
@pytest.fixture(scope="module")
def quote_agent():
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

    # Initialize the quote agent
    agent = ToolCallingAgent(
        model=model,
        tools=[search_quote_history, calculate_bulk_discount, get_available_paper_supplies],
        name="QuoteAgent",
        instructions="""
        You are a helpful agent. You will get quote request from client. You can search quote history to find appropriate discount.
        If no quote history is found, you can calculate bulk discount and generate quote.
        When searching for similar quotes or calculating bulk discount, drop the plurals. For example, 'A4 paper' instead of 'A4 papers'.
        Always use the exact item names from the paper_supplies list. You can use the get_available_paper_supplies tool 
        to get a list of all available paper supply item names. This ensures that the correct items are identified and processed.
        For example, 'Glossy paper' instead of 'glossy paper'. 
        Use this format for input of tools and output of your responses
        """,
        description="""
        The agent for generating quotes. It has access to tools such as generate_quote, calculate_bulk_discount, search_quote_history.
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

def test_calculate_bulk_discount():
    """Test the calculate_bulk_discount tool directly."""
    # Test with a valid item and quantity
    result = calculate_bulk_discount("A4 paper", 500)
    print(result)
    assert isinstance(result, BulkDiscountInfo)
    assert hasattr(result, 'item_name')
    assert hasattr(result, 'discount_percentage')
    assert hasattr(result, 'total_price')

    # Test with an item that doesn't exist in paper_supplies
    result = calculate_bulk_discount("Nonexistent Item", 100)
    print(result)
    assert isinstance(result, BulkDiscountInfo)
    assert result.error is not None
    assert "Invalid item name" in result.error

def test_search_quote_history():
    """Test the search_quote_history tool directly."""
    # Test with search terms that should return results
    result = search_quote_history(["Copy Paper"])
    assert isinstance(result, list)
    # The database should be initialized with some quotes
    if len(result) > 0:
        assert isinstance(result[0], dict)
        assert 'total_amount' in result[0]
#
# def test_generate_quote():
#     """Test the generate_quote tool directly."""
#     request = "I need 100 boxes of Copy Paper for my office."
#     result = generate_quote(request, "2025-08-01")
#     print()
#     print(result)
#     assert isinstance(result, Quote)
#     assert hasattr(result, 'items')
#     assert hasattr(result, 'total_amount')
#     assert hasattr(result, 'delivery_date')

def test_quote_agent_generate_quote(quote_agent):
    """Test the quote agent's ability to generate a quote."""
    query = "I need a quote for 100 boxes of A4 paper for delivery on September 15, 2025."
    response = quote_agent.run(query)

    # Verify the response contains relevant information
    print('\n', response)
    assert response is not None
    assert isinstance(response, str)
    # The response should mention Copy Paper
    assert "A4 paper" in response
    # The response should include pricing information
    # assert "$" in response or "price" in response.lower() or "cost" in response.lower()

def test_quote_agent_calculate_discount(quote_agent):
    """Test the quote agent's ability to calculate a bulk discount."""
    query = "What would be the discount if I order 500 boxes of A4 paper?"
    response = quote_agent.run(query)

    # Verify the response contains relevant information
    assert response is not None
    assert isinstance(response, str)
    # The response should mention discount
    assert "discount" in response.lower()
    # The response should include percentage or amount
    assert "%" in response or "$" in response

def test_quote_agent_exact_item_names(quote_agent):
    """Test the quote agent's ability to use exact item names from paper_supplies."""
    query = "I need a quote for 100 sheets of glossy paper for delivery on September 15, 2025."
    response = quote_agent.run(query)

    # Verify the response contains the exact item name from paper_supplies
    assert response is not None
    assert isinstance(response, str)
    # The response should use the exact item name "Glossy paper" instead of just "glossy paper"
    assert "Glossy paper" in response

# pytest will automatically discover and run the tests
