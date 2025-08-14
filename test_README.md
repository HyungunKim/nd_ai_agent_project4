# Agent Tests

This directory contains tests for the individual agents in the project. The tests verify that each agent is functional and can perform its intended tasks.

## Agents Tested

1. **InventoryAgent** - Tests the agent's ability to check inventory status and generate inventory reports.
2. **QuoteAgent** - Tests the agent's ability to generate quotes, calculate bulk discounts, and search quote history.
3. **OrderAgent** - Tests the agent's ability to process orders, check order status, and get supplier delivery dates.
4. **FinancialAgent** - Tests the agent's ability to get financial status, cash balance, and generate financial reports.
5. **Orchestrator** - Tests the agent's ability to coordinate the other agents and handle complex queries.
6. **Natural Language Tests** - Tests all agents with natural language inputs to verify they can understand and respond to conversational queries.

## Running the Tests

To run all tests, execute the following command:

```bash
python run_tests.py
```

Alternatively, you can use pytest directly:

```bash
pytest -v
```

To run tests for a specific agent, execute one of the following commands:

```bash
pytest test_inventory_agent.py -v
pytest test_quote_agent.py -v
pytest test_order_agent.py -v
pytest test_financial_agent.py -v
pytest test_orchestrator.py -v
pytest test_natural_language.py -v
```

You can also run a specific test function:

```bash
pytest test_inventory_agent.py::test_check_inventory_status -v
```

## Test Structure

Each test file follows a similar structure:

1. **Fixtures** - Pytest fixtures that initialize the model, database, and agent.
2. **Tool Tests** - Tests for the individual tools used by the agent.
3. **Agent Tests** - Tests for the agent's ability to respond to natural language queries.

## Environment Setup

The tests require the following environment variables to be set:

- `UDACITY_OPENAI_API_KEY` - The API key for OpenAI.

These can be set in a `.env` file in the project root directory.

## Dependencies

The tests depend on the following packages:

- pytest
- dotenv
- smolagents
- openai
- pandas
- sqlalchemy

These dependencies are listed in the project's `requirements.txt` file.
