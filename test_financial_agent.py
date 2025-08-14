import pytest
import os
import dotenv
from project_starter import (
    FinancialStatus,
    FinancialReport,
    get_financial_status,
    get_cash_balance,
    generate_financial_report,
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
        tools=[get_financial_status, get_cash_balance, generate_financial_report],
        name="FinancialAgent",
        description="""
        The agent for generating financial reports. It has access to tools such as get_financial_status, get_cash_balance, generate_financial_report.
        """
    )

    return agent

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

# pytest will automatically discover and run the tests
