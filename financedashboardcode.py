# Streamlit app configuration
import streamlit as st
import pandas as pd
import datetime as dt
import PyPDF2
import re
from datetime import datetime

st.set_page_config(page_title="Finance Dashboard", layout="wide")


def extract_key_numbers_from_pdf(file):
    try:
        # Open the PDF file
        pdf_reader = PyPDF2.PdfReader(file)
        
        # Extract text from all pages
        full_text = ""
        for page in pdf_reader.pages:
            full_text += page.extract_text()
        
        # Define regex patterns for financial data
        money_in_pattern = r"(?i)(?:money in|income|revenue|credits):?\s*\$?([\d,]+\.?\d*)"
        money_out_pattern = r"(?i)(?:money out|expenses|debits):?\s*\$?([\d,]+\.?\d*)"
        what_received_pattern = r"(?i)(?:what I received|received|proceeds):?\s*\$?([\d,]+\.?\d*)"
        date_pattern = r"\b(\d{1,2} (?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec) \d{4})\b"
        
        # Search for patterns
        money_in_matches = re.findall(money_in_pattern, full_text)
        money_out_matches = re.findall(money_out_pattern, full_text)
        what_received_matches = re.findall(what_received_pattern, full_text)
        date_matches = re.findall(date_pattern, full_text)

        # Convert matches to floats where applicable
        money_in = [float(match.replace(',', '')) for match in money_in_matches]
        money_out = [float(match.replace(',', '')) for match in money_out_matches]
        what_received = [float(match.replace(',', '')) for match in what_received_matches]

        # Create a summary
        # Display summary in a structured layout
        pol1, pol2, pol3, pol4 = st.columns(4)
        with pol1:
            st.metric("Money In", f"${sum(money_in):,.2f}")
        with pol2:
            st.metric("Money Out", f"${sum(money_out):,.2f}")
        with pol3:
            st.metric("Net Recieved", f"${sum(what_received):,.2f}")
        with pol4:
            formatted_date = date_matches[0]
            date_object = datetime.strptime(formatted_date, "%d %b %Y")

            # Format the datetime object into the desired format
            new_date = date_object.strftime("%d/%m/%Y")

            st.metric("On Date", str(new_date))
    except Exception as e:
        return None

# Streamlit app
st.title("Financial Dashboard")

# Sidebar for file uploads
st.sidebar.header("Upload Files")
uploaded_pdf = st.sidebar.file_uploader("Upload a PDF", type="pdf")

# Process the PDF file and extract data
results = None
if uploaded_pdf:
    st.write("## Rental Statement Summary")
    results = extract_key_numbers_from_pdf(uploaded_pdf)
# Display the dashboard if results are available
if results:
    # Display total income, expenses, and balance
    st.metric("Total Income", f"${results['Total Money In']:.2f}")
    st.metric("Total Expense", f"${results['Total Money Out']:.2f}")
    st.metric(
        "Remaining Balance",
        f"${results['Total Money In'] - results['Total Money Out']:.2f}",
    )

    # Display extracted dates in formatted style
    if results["Dates"]:
        st.write("### Key Dates")
        for date in results["Dates"]:
            formatted_date = re.sub(
                r"(\d{1,2}) (\w{3}) (\d{4})",
                lambda m: f"{int(m.group(1)):02d}/{m.group(2)}/{m.group(3)}",
                date,
            )
            st.write(f"- {formatted_date}")

else:
    st.sidebar.info("Please upload a Rental Statement PDF.")

st.markdown("---")


# Helper function to determine financial years in the dataset
def get_financial_years(data):
    start_year = data["Date"].dt.year.min()
    end_year = data["Date"].dt.year.max()
    financial_years = []
    for year in range(start_year - 1, end_year + 2):  # Cover edge cases
        fy_start = dt.date(year, 7, 1)
        fy_end = dt.date(year + 1, 6, 30)
        if not ((data["Date"] < pd.Timestamp(fy_start)).all() or (data["Date"] > pd.Timestamp(fy_end)).all()):
            financial_years.append(f"{year}-{year + 1}")
    return financial_years

# Sidebar for file upload
uploaded_file = st.sidebar.file_uploader("Upload a CSV file", type=["csv"])


if uploaded_file:
    st.write("## Bank Statement Summary")
    # Load and preprocess the data
    df = pd.read_csv(uploaded_file, dayfirst=True)
    df["Date"] = pd.to_datetime(df["Date"], format="%d/%m/%Y", errors="coerce")
    df.dropna(subset=["Date"], inplace=True)
    df["Debit"] = df["Debit"].abs()  # Convert debit to absolute values

    # Determine valid date range
    min_date = df["Date"].min().date()
    max_date = dt.date.today()

    # Calculate financial years dynamically
    financial_years = get_financial_years(df)

    # Sidebar for financial years
    st.sidebar.subheader("Financial Years")
    for fy in financial_years:
        start_year, end_year = map(int, fy.split('-'))
        fy_start = max(dt.date(start_year, 7, 1), min_date)
        fy_end = min(dt.date(end_year, 6, 30), max_date)
        if st.sidebar.button(f"{fy}"):
            st.session_state.start_date = fy_start
            st.session_state.end_date = fy_end

    # Sidebar for quick range buttons
    st.sidebar.subheader("Quick Ranges")
    if st.sidebar.button("Latest Month"):
        st.session_state.start_date = max_date - dt.timedelta(days=30)
        st.session_state.end_date = max_date

    if st.sidebar.button("Latest Fortnight"):
        st.session_state.start_date = max_date - dt.timedelta(days=14)
        st.session_state.end_date = max_date

    # Sidebar for custom date range
    st.sidebar.subheader("Select Date Range")
    st.session_state.start_date = st.sidebar.date_input(
        "Start Date",
        value=max(st.session_state.get("start_date", min_date), min_date),
        min_value=min_date,
        max_value=max_date,
    )
    st.session_state.end_date = st.sidebar.date_input(
        "End Date",
        value=min(st.session_state.get("end_date", max_date), max_date),
        min_value=min_date,
        max_value=max_date,
    )

    # Filter data based on date range
    filtered_data = df[
        (df["Date"] >= pd.Timestamp(st.session_state.start_date)) &
        (df["Date"] <= pd.Timestamp(st.session_state.end_date))
    ]

    # Calculate summary statistics
    total_income = filtered_data["Credit"].sum()
    total_expense = filtered_data["Debit"].sum()

    # Determine latest balance
    if not filtered_data.empty:
        latest_balance = filtered_data.sort_values(by="Date", ascending=False).iloc[0]["Balance"]
    else:
        latest_balance = 0.0

    # Determine next payment date for $1778.54
    payment_date_row = filtered_data[(filtered_data["Debit"] == 1778.54)].sort_values(by="Date", ascending=False)
    if not payment_date_row.empty:
        next_payment_date = (payment_date_row.iloc[0]["Date"] + pd.Timedelta(days=14)).strftime("%d/%m/%Y")
    else:
        next_payment_date = "No recent payment found"

    # Determine extra amount needed
    extra_amount_needed = max(0, 1778.54 - latest_balance)

    # Display summary in a structured layout
    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        st.metric("Total Income", f"${total_income:,.2f}")
    with col2:
        st.metric("Total Expense", f"${total_expense:,.2f}")
    with col3:
        st.metric("Latest Balance", f"${latest_balance:,.2f}")
    with col4:
        st.metric("Next Payment Date", str(next_payment_date))
    with col5:
        st.metric("Extra Amount Needed", f"${extra_amount_needed:,.2f}")


    # Filtered transactions and tables
    income_transactions = filtered_data[filtered_data["Credit"] > 0]
    expense_transactions = filtered_data[filtered_data["Debit"] > 0]

    # Initialize session state for toggling visibility
    if "show_income" not in st.session_state:
        st.session_state["show_income"] = False
    if "show_expense" not in st.session_state:
        st.session_state["show_expense"] = False

    # Functions to toggle visibility
    def toggle_income():
        st.session_state["show_income"] = not st.session_state["show_income"]

    def toggle_expense():
        st.session_state["show_expense"] = not st.session_state["show_expense"]

    # Ensure numeric columns are floats and round to 2 decimals
    income_transactions = income_transactions.copy()
    expense_transactions = expense_transactions.copy()

    # List of important keywords for filtering
    keywords = [
        "NRMA INSURANCE",
        "OSCAR PROPERTY",
        "Internal Transfer",
        "Osko Payment",
        "SUNCORP",
        "SWIFT transfer",
        "Trial",
    ]

    # Filter income transactions
    if not income_transactions.empty:
        numeric_cols_income = ["Credit", "Balance"]
        for col in numeric_cols_income:
            if col in income_transactions.columns:
                income_transactions[col] = pd.to_numeric(income_transactions[col], errors="coerce")
        income_transactions = income_transactions.round(2)

        if "Debit" in income_transactions.columns:
            income_transactions.drop(columns=["Debit"], inplace=True)
        if "Date" in income_transactions.columns:
            income_transactions["Date"] = income_transactions["Date"].dt.strftime("%d/%m/%Y")

    # Filter expense transactions
    if not expense_transactions.empty:
        numeric_cols_expense = ["Debit", "Balance"]
        for col in numeric_cols_expense:
            if col in expense_transactions.columns:
                expense_transactions[col] = pd.to_numeric(expense_transactions[col], errors="coerce")
        expense_transactions = expense_transactions.round(2)

        if "Credit" in expense_transactions.columns:
            expense_transactions.drop(columns=["Credit"], inplace=True)
        if "Date" in expense_transactions.columns:
            expense_transactions["Date"] = expense_transactions["Date"].dt.strftime("%d/%m/%Y")

    # Add filtering options
    st.markdown("### Filter by Keyword in Description")
    selected_keyword = st.selectbox("Select a keyword to filter transactions", ["All"] + keywords)

    if selected_keyword != "All":
        income_transactions = income_transactions[
            income_transactions["Description"].str.contains(selected_keyword, case=False, na=False)
        ]
        expense_transactions = expense_transactions[
            expense_transactions["Description"].str.contains(selected_keyword, case=False, na=False)
        ]

    # Layout for buttons and tables
    st.markdown("## Transaction Tables")

    # Toggle buttons
    st.button("Toggle All Income Transactions", on_click=toggle_income)
    st.button("Toggle All Expense Transactions", on_click=toggle_expense)

    # Display tables one below the other
    if st.session_state["show_income"]:
        st.write("### All Income Transactions")
        st.dataframe(income_transactions.style.format(precision=2), use_container_width=True)

    if st.session_state["show_expense"]:
        st.write("### All Expense Transactions")
        st.dataframe(expense_transactions.style.format(precision=2), use_container_width=True)


else:
    st.sidebar.info("Please upload a Bank Statement CSV file.")
