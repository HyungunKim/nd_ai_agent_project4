import pytest
import os
import dotenv
from project_starter import (
    FinancialStatus,
    FinancialReport,
    get_financial_status,
    get_cash_balance,
    generate_financial_report,
    get_available_paper_supplies,
    init_database,
    ToolCallingAgent,
    OpenAIServerModel
)

# Fixture for setting up the test environment
@pytest.fixture(scope="module")
def financial_agent():
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

    # Initialize the financial agent
    agent = ToolCallingAgent(
        model=model,
        tools=[get_financial_status, get_cash_balance, generate_financial_report, get_available_paper_supplies],
        name="FinancialAgent",
        instructions="Always use the exact item names from the paper_supplies list. You can use the get_available_paper_supplies tool "
                     "to get a list of all available paper supply item names. This ensures that the correct items are identified and processed."
                      "For example, 'Glossy paper' instead of 'glossy paper'. "
                      "Use this format for input of tools and output of your responses",
        description="""
        The agent for generating financial reports. It has access to tools such as get_financial_status, get_cash_balance, generate_financial_report.
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

def test_get_cash_balance():
    """Test the get_cash_balance tool directly."""
    result = get_cash_balance("2025-08-01")
    assert isinstance(result, float)
    # Cash balance should be a positive number
    assert result > 0

def test_generate_financial_report():
    """Test the generate_financial_report tool directly."""
    result = generate_financial_report("2025-08-01")
    assert isinstance(result, dict)
    assert 'as_of_date' in result
    assert 'cash_balance' in result
    assert 'inventory_value' in result
    assert 'total_assets' in result
    assert 'inventory_summary' in result
    assert 'top_selling_products' in result

def test_get_financial_status():
    """Test the get_financial_status tool directly."""
    result = get_financial_status("2028-01-01")
    assert isinstance(result, FinancialStatus)


def test_financial_agent_cash_balance(financial_agent):
    """Test the financial agent's ability to get cash balance."""
    query = "What is our cash balance as of January 1, 2023?"
    response = financial_agent.run(query)

    # Verify the response contains relevant information
    assert response is not None
    assert isinstance(response, str)
    assert float(response) == 0.0

    query = "What is our cash balance as of August 1, 2025?"
    response = financial_agent.run(query)
    assert response is not None
    assert isinstance(response, str)
    assert float(response) > 0.0

def test_financial_agent_financial_status(financial_agent):
    """Test the financial agent's ability to get financial status."""
    query = "What is our financial status as of August 1, 2025?"
    response = financial_agent.run(query)

    # Verify the response contains relevant information
    assert response is not None
    assert isinstance(response, str)
    # The response should mention financial terms
    assert any(term in response.lower() for term in ["asset", "liability", "cash", "inventory", "receivable", "payable"])

def test_financial_agent_exact_item_names(financial_agent):
    """Test the financial agent's ability to use exact item names from paper_supplies."""
    query = "What is the financial impact of our glossy paper sales as of August 1, 2025?"
    response = financial_agent.run(query)

    # Verify the response contains the exact item name from paper_supplies
    assert response is not None
    assert isinstance(response, str)
    # The response should use the exact item name "Glossy paper" instead of just "glossy paper"
    assert "Glossy paper" in response

# pytest will automatically discover and run the tests
