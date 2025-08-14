import pandas as pd
import numpy as np
import os
import time
import dotenv
import ast
from sqlalchemy.sql import text
from datetime import datetime, timedelta
from typing import Dict, List, Union, Optional
from sqlalchemy import create_engine, Engine
import logging
from pydantic import BaseModel, Field
from smolagents import (
    ToolCallingAgent,
    CodeAgent,
    OpenAIServerModel,
    tool,
)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(funcName)s - %(message)s', filename='project_output.log', filemode='w')

# Pydantic models for data structures
class PaperSupply(BaseModel):
    item_name: str
    category: str
    unit_price: float

class QuoteItem(BaseModel):
    item_name: str
    quantity: int
    unit_price: Optional[float] = None
    discount_percentage: Optional[float] = None
    total_price: Optional[float] = None

class Quote(BaseModel):
    request: str
    request_date: str
    items: List[QuoteItem]
    total_amount: float
    delivery_date: str
    explanation: str
    similar_quotes: Optional[List[Dict]] = None

class OrderItem(BaseModel):
    item_name: str
    quantity: int
    price: Optional[float] = None

class OrderResult(BaseModel):
    item_name: str
    quantity: int
    price: float
    status: str
    transaction_id: Optional[int] = None

class RestockItem(BaseModel):
    item_name: str
    quantity: int
    min_stock_level: int

class RestockResult(BaseModel):
    item_name: str
    quantity: int
    price: float
    status: str
    delivery_date: Optional[str] = None
    transaction_id: Optional[int] = None

class RestockReport(BaseModel):
    as_of_date: str
    restocked_items: List[RestockResult]
    total_items_restocked: int
    total_restock_cost: float

class Order(BaseModel):
    order_date: str
    order_results: List[OrderResult]
    total_sales_amount: float
    restock_results: List[RestockResult]
    all_items_processed: bool

class InventoryStatus(BaseModel):
    item_name: str
    available: bool
    requested_quantity: int
    current_stock: int
    min_stock_level: Optional[int] = None
    status: str
    needs_restock: bool
    restock_quantity: int

class InventoryItem(BaseModel):
    item_name: str
    category: str
    unit_price: float
    current_stock: int
    min_stock_level: int

class InventoryReport(BaseModel):
    as_of_date: str
    total_items: int
    items_in_stock: int
    items_below_threshold: int
    items_out_of_stock: int
    inventory_value: float
    items_below_threshold_list: List[InventoryItem]
    items_in_stock_list: List[InventoryItem]
    items_out_of_stock_list: List[InventoryItem]

class BulkDiscountInfo(BaseModel):
    item_name: str
    quantity: int
    unit_price: float
    discount_percentage: float
    discounted_unit_price: Optional[float] = None
    total_price: float
    error: Optional[str] = None

class OrderStatus(BaseModel):
    order_id: int
    status: str
    transaction_type: Optional[str] = None
    item_name: Optional[str] = None
    quantity: Optional[int] = None
    price: Optional[float] = None
    transaction_date: Optional[str] = None
    inventory_status: Optional[InventoryStatus] = None
    expected_delivery_date: Optional[str] = None
    details: Optional[str] = None

class FinancialReport(BaseModel):
    as_of_date: str
    total_sales: float
    total_expenses: float
    net_profit: float
    profit_margin: float
    inventory_value: float
    monthly_summary: Dict[str, Dict[str, float]]

class FinancialStatus(BaseModel):
    as_of_date: str
    cash_balance: float
    inventory_value: float
    total_assets: float
    revenue_30_days: float
    expenses_30_days: float
    profit_30_days: float
    profit_margin: float
    top_selling_products: List[Dict]
    recent_transactions: List[Dict]
    inventory_summary: List[Dict]

class RequestInfo(BaseModel):
    request_text: str
    request_date: str
    requested_items: List[Dict]
    requested_delivery_date: Optional[str] = None

# Create an SQLite database
logging.info('Logging started')
logging.info('Creating database connection')
db_engine = create_engine("sqlite:///munder_difflin.db")

# List containing the different kinds of papers
DEFUALT_MARKUP = 2.0
paper_supplies = [
    # Paper Types (priced per sheet unless specified)
    {"item_name": "A4 paper",                         "category": "paper",        "unit_price": 0.05},
    {"item_name": "Letter-sized paper",              "category": "paper",        "unit_price": 0.06},
    {"item_name": "Cardstock",                        "category": "paper",        "unit_price": 0.15},
    {"item_name": "Colored paper",                    "category": "paper",        "unit_price": 0.10},
    {"item_name": "Glossy paper",                     "category": "paper",        "unit_price": 0.20},
    {"item_name": "Matte paper",                      "category": "paper",        "unit_price": 0.18},
    {"item_name": "Recycled paper",                   "category": "paper",        "unit_price": 0.08},
    {"item_name": "Eco-friendly paper",               "category": "paper",        "unit_price": 0.12},
    {"item_name": "Poster paper",                     "category": "paper",        "unit_price": 0.25},
    {"item_name": "Banner paper",                     "category": "paper",        "unit_price": 0.30},
    {"item_name": "Kraft paper",                      "category": "paper",        "unit_price": 0.10},
    {"item_name": "Construction paper",               "category": "paper",        "unit_price": 0.07},
    {"item_name": "Wrapping paper",                   "category": "paper",        "unit_price": 0.15},
    {"item_name": "Glitter paper",                    "category": "paper",        "unit_price": 0.22},
    {"item_name": "Decorative paper",                 "category": "paper",        "unit_price": 0.18},
    {"item_name": "Letterhead paper",                 "category": "paper",        "unit_price": 0.12},
    {"item_name": "Legal-size paper",                 "category": "paper",        "unit_price": 0.08},
    {"item_name": "Crepe paper",                      "category": "paper",        "unit_price": 0.05},
    {"item_name": "Photo paper",                      "category": "paper",        "unit_price": 0.25},
    {"item_name": "Uncoated paper",                   "category": "paper",        "unit_price": 0.06},
    {"item_name": "Butcher paper",                    "category": "paper",        "unit_price": 0.10},
    {"item_name": "Heavyweight paper",                "category": "paper",        "unit_price": 0.20},
    {"item_name": "Standard copy paper",              "category": "paper",        "unit_price": 0.04},
    {"item_name": "Bright-colored paper",             "category": "paper",        "unit_price": 0.12},
    {"item_name": "Patterned paper",                  "category": "paper",        "unit_price": 0.15},

    # Product Types (priced per unit)
    {"item_name": "Paper plates",                     "category": "product",      "unit_price": 0.10},  # per plate
    {"item_name": "Paper cups",                       "category": "product",      "unit_price": 0.08},  # per cup
    {"item_name": "Paper napkins",                    "category": "product",      "unit_price": 0.02},  # per napkin
    {"item_name": "Disposable cups",                  "category": "product",      "unit_price": 0.10},  # per cup
    {"item_name": "Table covers",                     "category": "product",      "unit_price": 1.50},  # per cover
    {"item_name": "Envelopes",                        "category": "product",      "unit_price": 0.05},  # per envelope
    {"item_name": "Sticky notes",                     "category": "product",      "unit_price": 0.03},  # per sheet
    {"item_name": "Notepads",                         "category": "product",      "unit_price": 2.00},  # per pad
    {"item_name": "Invitation cards",                 "category": "product",      "unit_price": 0.50},  # per card
    {"item_name": "Flyers",                           "category": "product",      "unit_price": 0.15},  # per flyer
    {"item_name": "Party streamers",                  "category": "product",      "unit_price": 0.05},  # per roll
    {"item_name": "Decorative adhesive tape (washi tape)", "category": "product", "unit_price": 0.20},  # per roll
    {"item_name": "Paper party bags",                 "category": "product",      "unit_price": 0.25},  # per bag
    {"item_name": "Name tags with lanyards",          "category": "product",      "unit_price": 0.75},  # per tag
    {"item_name": "Presentation folders",             "category": "product",      "unit_price": 0.50},  # per folder

    # Large-format items (priced per unit)
    {"item_name": "Large poster paper (24x36 inches)", "category": "large_format", "unit_price": 1.00},
    {"item_name": "Rolls of banner paper (36-inch width)", "category": "large_format", "unit_price": 2.50},

    # Specialty papers
    {"item_name": "100 lb cover stock",               "category": "specialty",    "unit_price": 0.50},
    {"item_name": "80 lb text paper",                 "category": "specialty",    "unit_price": 0.40},
    {"item_name": "250 gsm cardstock",                "category": "specialty",    "unit_price": 0.30},
    {"item_name": "220 gsm poster paper",             "category": "specialty",    "unit_price": 0.35},
]

# Given below are some utility functions you can use to implement your multi-agent system

def generate_sample_inventory(paper_supplies: list, coverage: float = 0.4, seed: int = 137) -> pd.DataFrame:
    """
    Generate inventory for exactly a specified percentage of items from the full paper supply list.

    This function randomly selects exactly `coverage` × N items from the `paper_supplies` list,
    and assigns each selected item:
    - a random stock quantity between 200 and 800,
    - a minimum stock level between 50 and 150.

    The random seed ensures reproducibility of selection and stock levels.

    Args:
        paper_supplies (list): A list of dictionaries, each representing a paper item with
                               keys 'item_name', 'category', and 'unit_price'.
        coverage (float, optional): Fraction of items to include in the inventory (default is 0.4, or 40%).
        seed (int, optional): Random seed for reproducibility (default is 137).

    Returns:
        pd.DataFrame: A DataFrame with the selected items and assigned inventory values, including:
                      - item_name
                      - category
                      - unit_price
                      - current_stock
                      - min_stock_level
    """
    # Ensure reproducible random output
    np.random.seed(seed)

    # Calculate number of items to include based on coverage
    num_items = int(len(paper_supplies) * coverage)

    # Randomly select item indices without replacement
    selected_indices = np.random.choice(
        range(len(paper_supplies)),
        size=num_items,
        replace=False
    )

    # Extract selected items from paper_supplies list
    selected_items = [paper_supplies[i] for i in selected_indices]

    # Construct inventory records
    inventory = []
    for item in selected_items:
        inventory.append({
            "item_name": item["item_name"],
            "category": item["category"],
            "unit_price": item["unit_price"],
            "current_stock": np.random.randint(200, 800),  # Realistic stock range
            "min_stock_level": np.random.randint(50, 150)  # Reasonable threshold for reordering
        })

    # Return inventory as a pandas DataFrame
    return pd.DataFrame(inventory)

def init_database(db_engine: Engine = db_engine, seed: int = 137) -> Engine:
    """
    Set up the Munder Difflin database with all required tables and initial records.

    This function performs the following tasks:
    - Creates the 'transactions' table for logging stock orders and sales
    - Loads customer inquiries from 'quote_requests.csv' into a 'quote_requests' table
    - Loads previous quotes from 'quotes.csv' into a 'quotes' table, extracting useful metadata
    - Generates a random subset of paper inventory using `generate_sample_inventory`
    - Inserts initial financial records including available cash and starting stock levels

    Args:
        db_engine (Engine): A SQLAlchemy engine connected to the SQLite database.
        seed (int, optional): A random seed used to control reproducibility of inventory stock levels.
                              Default is 137.

    Returns:
        Engine: The same SQLAlchemy engine, after initializing all necessary tables and records.

    Raises:
        Exception: If an error occurs during setup, the exception is printed and raised.
    """
    try:
        # ----------------------------
        # 1. Create an empty 'transactions' table schema
        # ----------------------------
        with db_engine.connect() as conn:
            conn.execute(text("DROP TABLE transactions"))
            conn.execute(text("""
                              CREATE TABLE IF NOT EXISTS transactions
                              (
                                  id
                                  INTEGER
                                  PRIMARY
                                  KEY
                                  AUTOINCREMENT,
                                  item_name
                                  TEXT,
                                  transaction_type
                                  TEXT,
                                  units
                                  INTEGER,
                                  price
                                  REAL,
                                  transaction_date
                                  TEXT
                              )
                              """))

        # Set a consistent starting date
        initial_date = datetime(2025, 1, 1).isoformat()

        # ----------------------------
        # 2. Load and initialize 'quote_requests' table
        # ----------------------------
        quote_requests_df = pd.read_csv("quote_requests.csv")
        quote_requests_df["id"] = range(1, len(quote_requests_df) + 1)
        quote_requests_df.to_sql("quote_requests", db_engine, if_exists="replace", index=False)

        # ----------------------------
        # 3. Load and transform 'quotes' table
        # ----------------------------
        quotes_df = pd.read_csv("quotes.csv")
        quotes_df["request_id"] = range(1, len(quotes_df) + 1)
        quotes_df["order_date"] = initial_date

        # Unpack metadata fields (job_type, order_size, event_type) if present
        if "request_metadata" in quotes_df.columns:
            quotes_df["request_metadata"] = quotes_df["request_metadata"].apply(
                lambda x: ast.literal_eval(x) if isinstance(x, str) else x
            )
            quotes_df["job_type"] = quotes_df["request_metadata"].apply(lambda x: x.get("job_type", ""))
            quotes_df["order_size"] = quotes_df["request_metadata"].apply(lambda x: x.get("order_size", ""))
            quotes_df["event_type"] = quotes_df["request_metadata"].apply(lambda x: x.get("event_type", ""))

        # Retain only relevant columns
        quotes_df = quotes_df[[
            "request_id",
            "total_amount",
            "quote_explanation",
            "order_date",
            "job_type",
            "order_size",
            "event_type"
        ]]
        quotes_df.to_sql("quotes", db_engine, if_exists="replace", index=False)

        # ----------------------------
        # 4. Generate inventory and seed stock
        # ----------------------------
        inventory_df = generate_sample_inventory(paper_supplies, seed=seed)

        # Seed initial transactions
        initial_transactions = []

        # Add a starting cash balance via a dummy sales transaction
        initial_transactions.append({
            "item_name": None,
            "transaction_type": "sales",
            "units": None,
            "price": 50000.0,
            "transaction_date": initial_date,
        })

        # Add one stock order transaction per inventory item
        for _, item in inventory_df.iterrows():
            initial_transactions.append({
                "item_name": item["item_name"],
                "transaction_type": "stock_orders",
                "units": item["current_stock"],
                "price": item["current_stock"] * item["unit_price"] / DEFUALT_MARKUP,
                "transaction_date": initial_date,
            })

        # Commit transactions to database
        pd.DataFrame(initial_transactions).to_sql("transactions", db_engine, if_exists="append", index=False)

        # Save the inventory reference table
        inventory_df.to_sql("inventory", db_engine, if_exists="replace", index=False)

        return db_engine

    except Exception as e:
        print(f"Error initializing database: {e}")
        raise

def create_transaction(
    item_name: str,
    transaction_type: str,
    quantity: int,
    price: float,
    date: Union[str, datetime],
) -> int:
    """
    This function records a transaction of type 'stock_orders' or 'sales' with a specified
    item name, quantity, total price, and transaction date into the 'transactions' table of the database.

    Args:
        item_name (str): The name of the item involved in the transaction.
        transaction_type (str): Either 'stock_orders' or 'sales'.
        quantity (int): Number of units involved in the transaction.
        price (float): Total price of the transaction.
        date (str or datetime): Date of the transaction in ISO 8601 format.

    Returns:
        int: The ID of the newly inserted transaction.

    Raises:
        ValueError: If `transaction_type` is not 'stock_orders' or 'sales'.
        Exception: For other database or execution errors.
    """
    try:
        # Convert datetime to ISO string if necessary
        date_str = date.isoformat() if isinstance(date, datetime) else date

        # Validate transaction type
        if transaction_type not in {"stock_orders", "sales"}:
            raise ValueError("Transaction type must be 'stock_orders' or 'sales'")

        # Prepare transaction record as a single-row DataFrame
        transaction = pd.DataFrame([{
            "item_name": item_name,
            "transaction_type": transaction_type,
            "units": quantity,
            "price": price,
            "transaction_date": date_str,
        }])

        # Insert the record into the database
        transaction.to_sql("transactions", db_engine, if_exists="append", index=False)

        # Fetch and return the ID of the inserted row
        result = pd.read_sql("SELECT last_insert_rowid() as id", db_engine)
        return int(result.iloc[0]["id"])

    except Exception as e:
        print(f"Error creating transaction: {e}")
        raise

def get_all_inventory(as_of_date: str) -> Dict[str, int]:
    """
    Retrieve a snapshot of available inventory as of a specific date.

    This function calculates the net quantity of each item by summing 
    all stock orders and subtracting all sales up to and including the given date.

    Only items with positive stock are included in the result.

    Args:
        as_of_date (str): ISO-formatted date string (YYYY-MM-DD) representing the inventory cutoff.

    Returns:
        Dict[str, int]: A dictionary mapping item names to their current stock levels.
    """
    # SQL query to compute stock levels per item as of the given date
    query = """
        SELECT
            item_name,
            SUM(CASE
                WHEN transaction_type = 'stock_orders' THEN units
                WHEN transaction_type = 'sales' THEN -units
                ELSE 0
            END) as stock
        FROM transactions
        WHERE item_name IS NOT NULL
        AND transaction_date <= :as_of_date
        GROUP BY item_name
        HAVING stock > 0
    """

    # Execute the query with the date parameter
    result = pd.read_sql(query, db_engine, params={"as_of_date": as_of_date})

    # Convert the result into a dictionary {item_name: stock}
    return dict(zip(result["item_name"], result["stock"]))

def get_stock_level(item_name: str, as_of_date: Union[str, datetime]) -> pd.DataFrame:
    """
    Retrieve the stock level of a specific item as of a given date.

    This function calculates the net stock by summing all 'stock_orders' and 
    subtracting all 'sales' transactions for the specified item up to the given date.

    Args:
        item_name (str): The name of the item to look up.
        as_of_date (str or datetime): The cutoff date (inclusive) for calculating stock.

    Returns:
        pd.DataFrame: A single-row DataFrame with columns 'item_name' and 'current_stock'.
    """
    # Convert date to ISO string format if it's a datetime object
    if isinstance(as_of_date, datetime):
        as_of_date = as_of_date.isoformat()

    # SQL query to compute net stock level for the item
    stock_query = """
        SELECT
            item_name,
            COALESCE(SUM(CASE
                WHEN transaction_type = 'stock_orders' THEN units
                WHEN transaction_type = 'sales' THEN -units
                ELSE 0
            END), 0) AS current_stock
        FROM transactions
        WHERE item_name = :item_name
        AND transaction_date <= :as_of_date
    """

    # Execute query and return result as a DataFrame
    return pd.read_sql(
        stock_query,
        db_engine,
        params={"item_name": item_name, "as_of_date": as_of_date},
    )
@tool
def get_supplier_delivery_date(input_date_str: str, quantity: int) -> str:
    """
    Estimate the supplier delivery date based on the requested order quantity and a starting date.

    Delivery lead time increases with order size:
        - ≤10 units: same day
        - 11–100 units: 1 day
        - 101–1000 units: 4 days
        - >1000 units: 7 days

    Args:
        input_date_str (str): The starting date in ISO format (YYYY-MM-DD).
        quantity (int): The number of units in the order.

    Returns:
        str: Estimated delivery date in ISO format (YYYY-MM-DD).
    """
    # Debug log (comment out in production if needed)
    print(f"FUNC (get_supplier_delivery_date): Calculating for qty {quantity} from date string '{input_date_str}'")

    # Attempt to parse the input date
    try:
        input_date_dt = datetime.fromisoformat(input_date_str.split("T")[0])
    except (ValueError, TypeError):
        # Fallback to current date on format error
        print(f"WARN (get_supplier_delivery_date): Invalid date format '{input_date_str}', using today as base.")
        input_date_dt = datetime.now()

    # Determine delivery delay based on quantity
    if quantity <= 10:
        days = 0
    elif quantity <= 100:
        days = 1
    elif quantity <= 1000:
        days = 4
    else:
        days = 7

    # Add delivery days to the starting date
    delivery_date_dt = input_date_dt + timedelta(days=days)

    # Return formatted delivery date
    return delivery_date_dt.strftime("%Y-%m-%d")

@tool
def get_cash_balance(as_of_date: Union[str, datetime]) -> float:
    """
    Calculate the current cash balance as of a specified date.

    The balance is computed by subtracting total stock purchase costs ('stock_orders')
    from total revenue ('sales') recorded in the transactions table up to the given date.

    Args:
        as_of_date (str or datetime): The cutoff date (inclusive) in ISO format or as a datetime object.

    Returns:
        float: Net cash balance as of the given date. Returns 0.0 if no transactions exist or an error occurs.
    """
    try:
        # Convert date to ISO format if it's a datetime object
        if isinstance(as_of_date, datetime):
            as_of_date = as_of_date.isoformat()

        # Query all transactions on or before the specified date
        transactions = pd.read_sql(
            "SELECT * FROM transactions WHERE transaction_date <= :as_of_date",
            db_engine,
            params={"as_of_date": as_of_date},
        )

        # Compute the difference between sales and stock purchases
        if not transactions.empty:
            total_sales = transactions.loc[transactions["transaction_type"] == "sales", "price"].sum()
            total_purchases = transactions.loc[transactions["transaction_type"] == "stock_orders", "price"].sum()
            return float(total_sales - total_purchases)

        return 0.0

    except Exception as e:
        print(f"Error getting cash balance: {e}")
        return 0.0

@tool
def generate_financial_report(as_of_date: Union[str, datetime]) -> Dict:
    """
    Generate a complete financial report for the company as of a specific date.

    This includes:
    - Cash balance
    - Inventory valuation
    - Combined asset total
    - Itemized inventory breakdown
    - Top 5 best-selling products

    Args:
        as_of_date (str or datetime): The date (inclusive) for which to generate the report.

    Returns:
        Dict: A dictionary containing the financial report fields:
            - 'as_of_date': The date of the report
            - 'cash_balance': Total cash available
            - 'inventory_value': Total value of inventory
            - 'total_assets': Combined cash and inventory value
            - 'inventory_summary': List of items with stock and valuation details
            - 'top_selling_products': List of top 5 products by revenue
    """
    # Normalize date input
    if isinstance(as_of_date, datetime):
        as_of_date = as_of_date.isoformat()

    # Get current cash balance
    cash = get_cash_balance(as_of_date)

    # Get current inventory snapshot
    inventory_df = pd.read_sql("SELECT * FROM inventory", db_engine)
    inventory_value = 0.0
    inventory_summary = []

    # Compute total inventory value and summary by item
    for _, item in inventory_df.iterrows():
        stock_info = get_stock_level(item["item_name"], as_of_date)
        stock = stock_info["current_stock"].iloc[0]
        item_value = stock * item["unit_price"]
        inventory_value += item_value

        inventory_summary.append({
            "item_name": item["item_name"],
            "stock": stock,
            "unit_price": item["unit_price"],
            "value": item_value,
        })

    # Identify top-selling products by revenue
    top_sales_query = """
        SELECT item_name, SUM(units) as total_units, SUM(price) as total_revenue
        FROM transactions
        WHERE transaction_type = 'sales' AND transaction_date <= :date
        GROUP BY item_name
        ORDER BY total_revenue DESC
        LIMIT 5
    """
    top_sales = pd.read_sql(top_sales_query, db_engine, params={"date": as_of_date})
    top_selling_products = top_sales.to_dict(orient="records")

    return {
        "as_of_date": as_of_date,
        "cash_balance": cash,
        "inventory_value": inventory_value,
        "total_assets": cash + inventory_value,
        "inventory_summary": inventory_summary,
        "top_selling_products": top_selling_products,
    }

@tool
def search_quote_history(search_terms: List[str], limit: int = 5) -> List[Dict]:
    """
    Retrieve a list of historical quotes that match any of the provided search terms.

    The function searches both the original customer request (from `quote_requests`) and
    the explanation for the quote (from `quotes`) for each keyword. Results are sorted by
    most recent order date and limited by the `limit` parameter.

    Args:
        search_terms (List[str]): List of terms to match against customer requests and explanations.
        limit (int, optional): Maximum number of quote records to return. Default is 5.

    Returns:
        List[Dict]: A list of matching quotes, each represented as a dictionary with fields:
            - original_request
            - total_amount
            - quote_explanation
            - job_type
            - order_size
            - event_type
            - order_date
    """
    conditions = []
    params = {}

    # Build SQL WHERE clause using LIKE filters for each search term
    for i, term in enumerate(search_terms):
        param_name = f"term_{i}"
        conditions.append(
            f"(LOWER(qr.response) LIKE :{param_name} OR "
            f"LOWER(q.quote_explanation) LIKE :{param_name})"
        )
        params[param_name] = f"%{term.lower()}%"

    # Combine conditions; fallback to always-true if no terms provided
    where_clause = " AND ".join(conditions) if conditions else "1=1"

    # Final SQL query to join quotes with quote_requests
    query = f"""
        SELECT
            qr.response AS original_request,
            q.total_amount,
            q.quote_explanation,
            q.job_type,
            q.order_size,
            q.event_type,
            q.order_date
        FROM quotes q
        JOIN quote_requests qr ON q.request_id = qr.id
        WHERE {where_clause}
        ORDER BY q.order_date DESC
        LIMIT {limit}
    """
    # Execute parameterized query
    with db_engine.connect() as conn:
        result = conn.execute(text(query), params)
    df = pd.DataFrame(result.fetchall(), columns=["original_request", "total_amount", "quote_explanation", "job_type", "order_size", "event_type", "order_date"])
    return list(df.to_dict(orient='index').values())

########################
########################
########################
# YOUR MULTI AGENT STARTS HERE
########################
########################
########################


# Set up and load your env parameters and instantiate your model.

"""Set up tools for your agents to use, these should be methods that combine the database functions above
 and apply criteria to them to ensure that the flow of the system is correct."""

import dotenv
dotenv.load_dotenv()
openai_api_key = os.getenv("UDACITY_OPENAI_API_KEY")
model = OpenAIServerModel(
    model_id="gpt-4o-mini",
    api_base="https://openai.vocareum.com/v1",
    api_key=openai_api_key,
)

# Tools for inventory agent
@tool
def check_inventory_status(item_name: str, quantity: int, as_of_date: str) -> InventoryStatus:
    """
    Check if the requested item is available in sufficient quantity and provide inventory status.

    Args:
        item_name (str): The name of the item to check
        quantity (int): The requested quantity
        as_of_date (str): The date to check inventory as of

    Returns:
        InventoryStatus: A Pydantic model containing inventory status information
    """
    # Get current stock level
    stock_info = get_stock_level(item_name, as_of_date)

    if stock_info.empty:
        return InventoryStatus(
            item_name=item_name,
            available=False,
            requested_quantity=quantity,
            current_stock=0,
            status="Item not found in inventory",
            needs_restock=True,
            restock_quantity=quantity
        )

    current_stock = stock_info["current_stock"].iloc[0]

    # Check if we have enough stock
    available = current_stock >= quantity

    # Get minimum stock level from inventory table
    inventory_query = f"SELECT min_stock_level FROM inventory WHERE item_name = '{item_name}'"
    min_stock_result = pd.read_sql(inventory_query, db_engine)

    if min_stock_result.empty:
        min_stock_level = 100  # Default minimum stock level
    else:
        min_stock_level = min_stock_result["min_stock_level"].iloc[0]

    # Determine if restocking is needed
    remaining_stock = current_stock - quantity if available else current_stock
    needs_restock = remaining_stock < min_stock_level

    # Calculate restock quantity (to bring stock back to min_stock_level + buffer)
    buffer = 100  # Additional buffer stock
    restock_quantity = 0
    if needs_restock:
        restock_quantity = (min_stock_level + buffer) - remaining_stock

    return InventoryStatus(
        item_name=item_name,
        available=available,
        requested_quantity=quantity,
        current_stock=current_stock,
        min_stock_level=min_stock_level,
        status="Available" if available else "Insufficient stock",
        needs_restock=needs_restock,
        restock_quantity=restock_quantity if needs_restock else 0
    )

@tool
def restock_inventory(as_of_date: str, buffer_multiplier: float = 1.5) -> RestockReport:
    """
    Restock inventory items that are below their minimum stock levels.

    This function identifies items that are below their minimum stock levels,
    creates stock_orders transactions to restock them, and returns information
    about the restocked items.

    Args:
        as_of_date (str): The date to restock inventory as of
        buffer_multiplier (float, optional): Multiplier for the buffer stock. 
                                            Default is 1.5, meaning items will be 
                                            restocked to 1.5 times their minimum level.

    Returns:
        RestockReport: A Pydantic model containing information about the restocked items
    """
    # Get inventory report to identify items below threshold
    inventory_report = get_inventory_report(as_of_date)

    # Items to restock are those below threshold
    items_to_restock = inventory_report.items_below_threshold_list + inventory_report.items_out_of_stock_list

    # Process restocking for items that need it
    restock_results = []
    total_restock_cost = 0.0

    for item in items_to_restock:
        item_name = item.item_name
        min_stock_level = item.min_stock_level
        current_stock = item.current_stock

        # Calculate restock quantity to bring stock to min_stock_level * buffer_multiplier
        target_stock = int(min_stock_level * buffer_multiplier)
        restock_quantity = target_stock - current_stock

        # Get unit price from inventory
        inventory_query = f"SELECT unit_price FROM inventory WHERE item_name = '{item_name}'"
        price_result = pd.read_sql(inventory_query, db_engine)

        if not price_result.empty:
            unit_price = price_result["unit_price"].iloc[0]
            restock_price = restock_quantity * unit_price / DEFUALT_MARKUP  # Cost to restock

            # Calculate supplier delivery date
            supplier_delivery_date = get_supplier_delivery_date(as_of_date, restock_quantity)

            try:
                # Create stock order transaction
                transaction_id = create_transaction(
                    item_name=item_name,
                    transaction_type="stock_orders",
                    quantity=restock_quantity,
                    price=restock_price,
                    date=supplier_delivery_date
                )

                # Add to restock results
                restock_results.append(RestockResult(
                    item_name=item_name,
                    quantity=restock_quantity,
                    price=restock_price,
                    status="Restocked",
                    delivery_date=supplier_delivery_date,
                    transaction_id=transaction_id
                ))

                total_restock_cost += restock_price

            except Exception as e:
                # Add failed restock to results
                restock_results.append(RestockResult(
                    item_name=item_name,
                    quantity=restock_quantity,
                    price=0.0,
                    status=f"Error: {str(e)}",
                    delivery_date=None,
                    transaction_id=None
                ))

    # Create and return the restock report
    return RestockReport(
        as_of_date=as_of_date,
        restocked_items=restock_results,
        total_items_restocked=len(restock_results),
        total_restock_cost=total_restock_cost
    )

@tool
def get_inventory_report(as_of_date: str) -> InventoryReport:
    """
    Generate a comprehensive inventory report as of a specific date.

    Args:
        as_of_date (str): The date to generate the report for

    Returns:
        InventoryReport: A Pydantic model containing inventory report information
    """
    # Get all inventory items
    inventory_df = pd.read_sql("SELECT * FROM inventory", db_engine)

    # Get current stock levels for all items
    current_inventory = get_all_inventory(as_of_date)

    # Prepare report data
    items_below_threshold_list = []
    items_in_stock_list = []
    items_out_of_stock_list = []
    inventory_value = 0

    for _, item in inventory_df.iterrows():
        item_name = item["item_name"]
        min_stock_level = item["min_stock_level"]
        unit_price = item["unit_price"]
        category = item["category"]

        # Get current stock level
        current_stock = current_inventory.get(item_name, 0)

        # Calculate inventory value
        item_value = current_stock * unit_price
        inventory_value += item_value

        # Create InventoryItem
        inventory_item = InventoryItem(
            item_name=item_name,
            category=category,
            unit_price=unit_price,
            current_stock=current_stock,
            min_stock_level=min_stock_level
        )

        # Categorize items
        if current_stock == 0:
            items_out_of_stock_list.append(inventory_item)
        elif current_stock < min_stock_level:
            items_below_threshold_list.append(inventory_item)
        else:
            items_in_stock_list.append(inventory_item)

    return InventoryReport(
        as_of_date=as_of_date,
        total_items=len(inventory_df),
        items_in_stock=len(items_in_stock_list),
        items_below_threshold=len(items_below_threshold_list),
        items_out_of_stock=len(items_out_of_stock_list),
        inventory_value=inventory_value,
        items_below_threshold_list=items_below_threshold_list,
        items_in_stock_list=items_in_stock_list,
        items_out_of_stock_list=items_out_of_stock_list
    )


# Tools for quoting agent
@tool
def calculate_bulk_discount(item_name: str, quantity: int) -> BulkDiscountInfo:
    """
    Calculate the appropriate bulk discount for an item based on quantity.

    Args:
        item_name (str): The name of the item
        quantity (int): The quantity ordered

    Returns:
        BulkDiscountInfo: A Pydantic model containing discount information
    """
    # Get the base unit price for the item
    inventory_query = f"SELECT unit_price FROM inventory WHERE item_name = '{item_name}'"
    price_result = pd.read_sql(inventory_query, db_engine)

    if price_result.empty:
        # Try to find in paper_supplies if not in inventory
        for item in paper_supplies:
            if item["item_name"] == item_name:
                unit_price = item["unit_price"]
                break
        else:
            return BulkDiscountInfo(
                item_name=item_name,
                quantity=quantity,
                unit_price=0,
                discount_percentage=0,
                discounted_unit_price=0,
                total_price=0,
                error="Item not found"
            )
    else:
        unit_price = price_result["unit_price"].iloc[0]

    # Calculate discount percentage based on quantity
    if quantity < 100:
        discount_percentage = 0
    elif quantity < 500:
        discount_percentage = 5
    elif quantity < 1000:
        discount_percentage = 10
    else:
        discount_percentage = 15

    # Apply discount
    discounted_unit_price = unit_price * (1 - discount_percentage / 100)
    total_price = discounted_unit_price * quantity

    return BulkDiscountInfo(
        item_name=item_name,
        quantity=quantity,
        unit_price=unit_price,
        discount_percentage=discount_percentage,
        discounted_unit_price=discounted_unit_price,
        total_price=total_price
    )

@tool
def format_quote_explanation(items: List[Dict], total_amount: float, delivery_date: str) -> str:
    """
    Format a detailed quote explanation with breakdown of costs.

    Args:
        items (List[Dict]): List of items with their quantities and prices
        total_amount (float): The total amount for the quote
        delivery_date (str): The expected delivery date

    Returns:
        str: A formatted quote explanation
    """
    explanation = "Thank you for your order! "

    # Add details for each item
    for item in items:
        item_name = item["item_name"]
        quantity = item["quantity"]
        unit_price = item["unit_price"]
        discount_percentage = item["discount_percentage"]
        total_price = item["total_price"]

        if discount_percentage > 0:
            explanation += f"For {quantity} {item_name} at ${unit_price:.2f} each with a {discount_percentage}% bulk discount, the cost is ${total_price:.2f}. "
        else:
            explanation += f"For {quantity} {item_name} at ${unit_price:.2f} each, the cost is ${total_price:.2f}. "

    # Add total and delivery information
    explanation += f"The total cost for your order is ${total_amount:.2f}, and it will be delivered by {delivery_date}."

    return explanation

# @tool
# def generate_quote(request: str, request_date: str) -> Quote:
#     """
#     Generate a complete quote based on a customer request.
#
#     Args:
#         request (str): The customer request text
#         request_date (str): The date of the request
#
#     Returns:
#         Quote: A Pydantic model containing the complete quote information
#     """
#     # Extract items and quantities from the request
#     # This is a simplified version - in a real system, this would use NLP
#     quote_items = []
#
#     # Look for common paper types in the request
#     for item in paper_supplies:
#         item_name = item["item_name"].lower()
#         if item_name in request.lower():
#             # Try to find quantity before the item name
#             request_lower = request.lower()
#             item_index = request_lower.find(item_name)
#
#             # Look for numbers before the item name
#             quantity = 100  # Default quantity
#
#             # Simple regex to find numbers before the item name
#             import re
#             quantity_matches = re.findall(r'(\d+)\s+(?:sheets|reams|rolls|packs|boxes)?\s+(?:of\s+)?(?:.*?)?' + re.escape(item_name), request_lower)
#
#             if quantity_matches:
#                 quantity = int(quantity_matches[0])
#
#             quote_items.append(QuoteItem(
#                 item_name=item["item_name"],
#                 quantity=quantity
#             ))
#
#     # If no items were found, add some default items
#     if not quote_items:
#         quote_items.append(QuoteItem(
#             item_name="A4 paper",
#             quantity=500
#         ))
#
#     # Calculate prices and discounts for each item
#     total_amount = 0
#     for i, item in enumerate(quote_items):
#         discount_info = calculate_bulk_discount(item.item_name, item.quantity)
#         quote_items[i].unit_price = discount_info.unit_price
#         quote_items[i].discount_percentage = discount_info.discount_percentage
#         quote_items[i].total_price = discount_info.total_price
#         total_amount += discount_info.total_price
#
#     # Round total to a nice number
#     total_amount = round(total_amount)
#
#     # Calculate delivery date
#     # Assume delivery is 7 days from request date
#     from datetime import datetime, timedelta
#     request_date_dt = datetime.fromisoformat(request_date.split("T")[0] if "T" in request_date else request_date)
#     delivery_date = (request_date_dt + timedelta(days=7)).strftime("%Y-%m-%d")
#
#     # Format explanation
#     # Convert Pydantic models to dictionaries for compatibility with existing function
#     items_dict = [item.model_dump() for item in quote_items]
#     explanation = format_quote_explanation(items_dict, total_amount, delivery_date)
#
#     # Look for similar quotes in history
#     search_terms = [item.item_name for item in quote_items]
#     similar_quotes = search_quote_history(search_terms)
#
#     # Create and return the Quote object
#     return Quote(
#         request=request,
#         request_date=request_date,
#         items=quote_items,
#         total_amount=total_amount,
#         delivery_date=delivery_date,
#         explanation=explanation,
#         similar_quotes=similar_quotes
#     )


# Tools for ordering agent1
@tool
def process_order(items: List[Union[Dict, OrderItem]], order_date: str) -> Order:
    """
    Process an order by creating sales transactions and arranging for restocking if needed.

    Args:
        items (List[Union[Dict, OrderItem]]): List of items with their quantities and prices
            class OrderItem(BaseModel):
                item_name: str
                quantity: int
                price: Optional[float] = None
        order_date (str): The date of the order

    Returns:
        Order: A Pydantic model containing order processing information
    """
    logging.info("Processing order...")
    order_results = []
    total_sales_amount = 0
    restock_items = []

    for item in items:
        # Handle both Dict and OrderItem inputs
        if isinstance(item, OrderItem):
            item_name = item.item_name
            quantity = item.quantity
            price = item.price or 0
        else:
            item_name = item["item_name"]
            quantity = item["quantity"]
            price = item.get("total_price", 0)

        # Check inventory status
        inventory_status = check_inventory_status(item_name, quantity, order_date)

        if inventory_status.available:
            # Create sales transaction
            try:
                transaction_id = create_transaction(
                    item_name=item_name,
                    transaction_type="sales",
                    quantity=quantity,
                    price=price,
                    date=order_date
                )

                order_results.append(OrderResult(
                    item_name=item_name,
                    quantity=quantity,
                    price=price,
                    status="Processed",
                    transaction_id=transaction_id
                ))

                total_sales_amount += price

                # Check if restocking is needed
                if inventory_status.needs_restock:
                    restock_items.append(RestockItem(
                        item_name=item_name,
                        quantity=inventory_status.restock_quantity,
                        min_stock_level=inventory_status.min_stock_level
                    ))
            except Exception as e:
                order_results.append(OrderResult(
                    item_name=item_name,
                    quantity=quantity,
                    price=price,
                    status=f"Error: {str(e)}",
                    transaction_id=None
                ))
        else:
            order_results.append(OrderResult(
                item_name=item_name,
                quantity=quantity,
                price=price,
                status="Insufficient stock",
                transaction_id=None
            ))

            # Add to restock items
            restock_items.append(RestockItem(
                item_name=item_name,
                quantity=max(quantity, inventory_status.restock_quantity),
                min_stock_level=inventory_status.min_stock_level or 100
            ))

    # Process restocking for items that need it
    restock_results = []
    for restock_item in restock_items:
        item_name = restock_item.item_name
        restock_quantity = restock_item.quantity

        # Get unit price from inventory
        inventory_query = f"SELECT unit_price FROM inventory WHERE item_name = '{item_name}'"
        price_result = pd.read_sql(inventory_query, db_engine)

        if not price_result.empty:
            unit_price = price_result["unit_price"].iloc[0]
            restock_price = restock_quantity * unit_price / DEFUALT_MARKUP  # Cost to restock

            # Calculate supplier delivery date
            supplier_delivery_date = get_supplier_delivery_date(order_date, restock_quantity)

            try:
                # Create stock order transaction
                transaction_id = create_transaction(
                    item_name=item_name,
                    transaction_type="stock_orders",
                    quantity=restock_quantity,
                    price=restock_price,
                    date=supplier_delivery_date
                )

                restock_results.append(RestockResult(
                    item_name=item_name,
                    quantity=restock_quantity,
                    price=restock_price,
                    status="Restocked",
                    delivery_date=supplier_delivery_date,
                    transaction_id=transaction_id
                ))
            except Exception as e:
                restock_results.append(RestockResult(
                    item_name=item_name,
                    quantity=restock_quantity,
                    price=restock_price,
                    status=f"Restock Error: {str(e)}",
                    delivery_date=supplier_delivery_date,
                    transaction_id=None
                ))
        else:
            restock_results.append(RestockResult(
                item_name=item_name,
                quantity=restock_quantity,
                price=0,
                status="Item not found in inventory",
                delivery_date=None,
                transaction_id=None
            ))
    return Order(
        order_date=order_date,
        total_sales_amount=total_sales_amount,
        order_results=order_results,
        restock_results=restock_results,
        all_items_processed=all(result.status == "Processed" for result in order_results)
    )

@tool
def check_order_status(order_id: int, as_of_date: str) -> OrderStatus:
    """
    Check the status of an order based on its transactions.

    Args:
        order_id (int): The ID of the order to check
        as_of_date (str): The date to check the status as of

    Returns:
        OrderStatus: A Pydantic model containing order status information
    """
    # In a real system, we would have an orders table to track this
    # For this implementation, we'll use the transaction ID as the order ID

    # Get the transaction
    query = f"""
        SELECT * FROM transactions 
        WHERE id = {order_id} 
        AND transaction_date <= '{as_of_date}'
    """

    transaction = pd.read_sql(query, db_engine)

    if transaction.empty:
        return OrderStatus(
            order_id=order_id,
            status="Not found",
            details="No transaction found with this ID"
        )

    # Get transaction details
    transaction_type = transaction["transaction_type"].iloc[0]
    item_name = transaction["item_name"].iloc[0]
    quantity = transaction["units"].iloc[0]
    price = transaction["price"].iloc[0]
    transaction_date = transaction["transaction_date"].iloc[0]

    if transaction_type == "sales":
        # Check if the item is still in stock
        inventory_status = check_inventory_status(item_name, quantity, as_of_date)

        return OrderStatus(
            order_id=order_id,
            status="Completed" if inventory_status.available else "Partially Fulfilled",
            transaction_type=transaction_type,
            item_name=item_name,
            quantity=quantity,
            price=price,
            transaction_date=transaction_date,
            inventory_status=inventory_status
        )
    else:  # stock_orders
        # Calculate expected delivery date
        supplier_delivery_date = get_supplier_delivery_date(transaction_date, quantity)

        # Check if the delivery date has passed
        from datetime import datetime
        as_of_date_dt = datetime.fromisoformat(as_of_date.split("T")[0] if "T" in as_of_date else as_of_date)
        delivery_date_dt = datetime.fromisoformat(supplier_delivery_date)

        status = "Delivered" if as_of_date_dt >= delivery_date_dt else "In Transit"

        return OrderStatus(
            order_id=order_id,
            status=status,
            transaction_type=transaction_type,
            item_name=item_name,
            quantity=quantity,
            price=price,
            transaction_date=transaction_date,
            expected_delivery_date=supplier_delivery_date
        )


# Tools for financial agent
@tool
def get_financial_status(as_of_date: str) -> FinancialStatus:
    """
    Get comprehensive financial status information as of a specific date.

    Args:
        as_of_date (str): The date to get financial status for

    Returns:
        FinancialStatus: A Pydantic model containing financial status information
    """
    # Generate a complete financial report
    financial_report = generate_financial_report(as_of_date)

    # Get cash balance
    cash_balance = financial_report["cash_balance"]

    # Get inventory value
    inventory_value = financial_report["inventory_value"]

    # Get top selling products
    top_selling_products = financial_report["top_selling_products"]

    # Calculate total assets
    total_assets = cash_balance + inventory_value

    # Get recent transactions
    recent_transactions_query = f"""
        SELECT * FROM transactions
        WHERE transaction_date <= '{as_of_date}'
        ORDER BY transaction_date DESC
        LIMIT 10
    """
    recent_transactions = pd.read_sql(recent_transactions_query, db_engine).to_dict(orient="records")

    # Calculate revenue and expenses for the last 30 days
    from datetime import datetime, timedelta
    as_of_date_dt = datetime.fromisoformat(as_of_date.split("T")[0] if "T" in as_of_date else as_of_date)
    thirty_days_ago = (as_of_date_dt - timedelta(days=30)).isoformat()

    revenue_query = f"""
        SELECT SUM(price) as revenue
        FROM transactions
        WHERE transaction_type = 'sales'
        AND transaction_date BETWEEN '{thirty_days_ago}' AND '{as_of_date}'
    """
    revenue_result = pd.read_sql(revenue_query, db_engine)
    revenue_30_days = float(revenue_result["revenue"].iloc[0]) if not revenue_result.empty and not pd.isna(revenue_result["revenue"].iloc[0]) else 0.0

    expenses_query = f"""
        SELECT SUM(price) as expenses
        FROM transactions
        WHERE transaction_type = 'stock_orders'
        AND transaction_date BETWEEN '{thirty_days_ago}' AND '{as_of_date}'
    """
    expenses_result = pd.read_sql(expenses_query, db_engine)
    expenses_30_days = float(expenses_result["expenses"].iloc[0]) if not expenses_result.empty and not pd.isna(expenses_result["expenses"].iloc[0]) else 0.0

    # Calculate profit for the last 30 days
    profit_30_days = revenue_30_days - expenses_30_days

    # Calculate profit margin
    profit_margin = (profit_30_days / revenue_30_days * 100) if revenue_30_days > 0 else 0

    return FinancialStatus(
        as_of_date=as_of_date,
        cash_balance=cash_balance,
        inventory_value=inventory_value,
        total_assets=total_assets,
        revenue_30_days=revenue_30_days,
        expenses_30_days=expenses_30_days,
        profit_30_days=profit_30_days,
        profit_margin=profit_margin,
        top_selling_products=top_selling_products,
        recent_transactions=recent_transactions,
        inventory_summary=financial_report["inventory_summary"]
    )

# tool for orchestrator agent
@tool
def parse_request(request: str) -> RequestInfo:
    """
    Parse a customer request to extract key information.

    Args:
        request (str): The customer request text

    Returns:
        RequestInfo: A Pydantic model containing extracted information from the request
    """
    # Extract date from request if present
    import re
    date_match = re.search(r'Date of request: (\d{4}-\d{2}-\d{2})', request)
    request_date = date_match.group(1) if date_match else datetime.now().strftime("%Y-%m-%d")

    # Look for common paper types in the request
    requested_items = []
    for item in paper_supplies:
        item_name = item["item_name"].lower()
        if item_name in request.lower():
            # Try to find quantity before the item name
            quantity_matches = re.findall(r'(\d+)\s+(?:sheets|reams|rolls|packs|boxes)?\s+(?:of\s+)?(?:.*?)?' + re.escape(item_name), request.lower())

            quantity = 100  # Default quantity
            if quantity_matches:
                quantity = int(quantity_matches[0])

            requested_items.append({
                "item_name": item["item_name"],
                "quantity": quantity
            })

    # Extract delivery date if present
    delivery_match = re.search(r'(?:deliver|delivery).*?by\s+(\w+\s+\d+,?\s+\d{4})', request, re.IGNORECASE)
    delivery_date = None
    if delivery_match:
        try:
            from dateutil import parser
            delivery_date = parser.parse(delivery_match.group(1)).strftime("%Y-%m-%d")
        except:
            delivery_date = None

    return RequestInfo(
        request_text=request,
        request_date=request_date,
        requested_items=requested_items,
        requested_delivery_date=delivery_date
    )

# Set up your agents and create an orchestration agent that will manage them.
# Define the agents using the smolagents framework

# Financial Agent
class FinancialAgent(ToolCallingAgent):
    def __init__(self, model):
        super().__init__


# Initialize the agents
inventory_agent = ToolCallingAgent(model=model,
                         tools=[check_inventory_status, get_inventory_report, restock_inventory],
                         name="InventoryAgent",
                         description="""
                         The agent for handling inventory logic. It has access to tools such as check_inventory_status, get_inventory_report, and restock_inventory.
                         """)

quote_agent = ToolCallingAgent(model=model,
                         tools=[search_quote_history, calculate_bulk_discount],
                         name="QuoteAgent",
                         description="""
                         The agent for generating quotes. It has access to tools `search_quote_history` to find past quotes. Apply bulk discount where there was similar preceding quote history to be fair.
                         """)
order_agent = ToolCallingAgent(model=model,
                         tools=[process_order, check_order_status, get_supplier_delivery_date],
                         name="OrderAgent",
                         description="""
                         The agent for processing orders. It has access to tools such as `process_order`, `check_order_status`, `get_supplier_delivery_date`.
                         """)
financial_agent = ToolCallingAgent(model=model,
                         tools=[get_financial_status, get_cash_balance],
                         name="FinancialAgent",
                         description="""
                         The agent for generating financial reports. It has access to tools such as `get_financial_status`, `get_cash_balance`.
                         """)
orchestrator = ToolCallingAgent(model=model,
                         tools=[parse_request],
                         instructions="You are a helpful agent. You will get quote request from client. "
                                      "You have to check inventory status, check previous quote history "
                                      "to find appropriate discount, generate quote, process order, "
                                      "There are other agents that can help you.",
                         managed_agents=[inventory_agent, quote_agent, order_agent, financial_agent])


# Run your test scenarios by writing them here. Make sure to keep track of them.

def run_test_scenarios():

    print("Initializing Database...")
    init_database()
    try:
        quote_requests_sample = pd.read_csv("quote_requests_sample.csv")
        quote_requests_sample["request_date"] = pd.to_datetime(
            quote_requests_sample["request_date"], format="%m/%d/%y", errors="coerce"
        )
        quote_requests_sample.dropna(subset=["request_date"], inplace=True)
        quote_requests_sample = quote_requests_sample.sort_values("request_date")
    except Exception as e:
        print(f"FATAL: Error loading test data: {e}")
        return

    quote_requests_sample = pd.read_csv("quote_requests_sample.csv")

    # Sort by date
    quote_requests_sample["request_date"] = pd.to_datetime(
        quote_requests_sample["request_date"]
    )
    quote_requests_sample = quote_requests_sample.sort_values("request_date")

    # Get initial state
    initial_date = quote_requests_sample["request_date"].min().strftime("%Y-%m-%d")
    report = generate_financial_report(initial_date)
    current_cash = report["cash_balance"]
    current_inventory = report["inventory_value"]

    # Our multi-agent system is already initialized above
    # We have:
    # - inventory_agent: For inventory operations
    # - quote_agent: For generating quotes
    # - order_agent: For order fulfillment
    # - financial_agent: For financial operations
    # - orchestrator: The main agent that coordinates everything

    results = []
    for idx, row in quote_requests_sample.iterrows():
        request_date = row["request_date"].strftime("%Y-%m-%d")

        print(f"\n=== Request {idx+1} ===")
        print(f"Context: {row['job']} organizing {row['event']}")
        print(f"Request Date: {request_date}")
        print(f"Cash Balance: ${current_cash:.2f}")
        print(f"Inventory Value: ${current_inventory:.2f}")

        # Process request
        request_with_date = f"{row['request']} (Date of request: {request_date})"

        # Use our orchestrator agent to handle the request
        response = orchestrator.run(request_with_date, max_steps=5, reset=True)

        # Update state
        report = generate_financial_report(request_date)
        current_cash = report["cash_balance"]
        current_inventory = report["inventory_value"]

        print(f"Response: {response}")
        print(f"Updated Cash: ${current_cash:.2f}")
        print(f"Updated Inventory: ${current_inventory:.2f}")

        results.append(
            {
                "request_id": idx + 1,
                "request_date": request_date,
                "cash_balance": current_cash,
                "inventory_value": current_inventory,
                "response": response,
            }
        )

        time.sleep(1)

    # Final report
    final_date = quote_requests_sample["request_date"].max().strftime("%Y-%m-%d")
    final_report = generate_financial_report(final_date)
    print("\n===== FINAL FINANCIAL REPORT =====")
    print(f"Final Cash: ${final_report['cash_balance']:.2f}")
    print(f"Final Inventory: ${final_report['inventory_value']:.2f}")

    # Save results
    pd.DataFrame(results).to_csv("test_results.csv", index=False)
    return results


if __name__ == "__main__":
    results = run_test_scenarios()
