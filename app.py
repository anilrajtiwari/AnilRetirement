import streamlit as st
import pandas as pd
from io import BytesIO

# ---------------------------------
# PAGE SETUP
# ---------------------------------
st.set_page_config(page_title="Anil's Retirement Simulator ", layout="wide")
st.title("Anil's Retirement Planning Simulator ")
st.caption("Audit-safe Three Bucket Strategy | Educational Use")

# ---------------------------------
# INPUTS
# ---------------------------------
st.sidebar.header("Employee Inputs")

current_age = st.sidebar.number_input("Current Age", 30, 59, 55)
retirement_age = st.sidebar.number_input("Retirement Age", current_age + 1, 65, 60)
life_expectancy = st.sidebar.number_input("Life Expectancy", retirement_age + 1, 100, 85)

monthly_expense_today = st.sidebar.number_input(
    "Current Monthly Expense (₹)", 0, 500000, 75000, step=5000
)

inflation = st.sidebar.slider("Expected Inflation (%)", 3.0, 10.0, 6.0) / 100

monthly_pension = st.sidebar.number_input(
    "Monthly Pension (₹)", 0, 300000, 40000, step=5000
)

total_corpus = st.sidebar.number_input(
    "Total Retirement Corpus (₹)", 0, 50000000, 11000000, step=500000
)

st.sidebar.subheader("Expected Returns")
r1 = st.sidebar.slider("Bucket 1 Return (%)", 2.0, 6.0, 4.0) / 100
r2 = st.sidebar.slider("Bucket 2 Return (%)", 4.0, 8.0, 6.0) / 100
r3 = st.sidebar.slider("Bucket 3 Return (%)", 7.0, 12.0, 9.0) / 100

st.sidebar.subheader("Stress Scenarios")
crash_years = st.sidebar.selectbox(
    "Market Crash Duration",
    ["No Crash", "3 Years", "5 Years"]
)
inflation_shock = st.sidebar.checkbox(
    "High Inflation (+4%) in First 5 Years After Retirement"
)

run = st.sidebar.button("Run Simulation")

# ---------------------------------
# LOGIC
# ---------------------------------
if run:

    years_to_retirement = retirement_age - current_age

    monthly_expense_retirement = monthly_expense_today * ((1 + inflation) ** years_to_retirement)
    annual_expense_base = monthly_expense_retirement * 12
    annual_pension = monthly_pension * 12

    st.subheader(f"At Retirement (Age {retirement_age})")
    c1, c2, c3 = st.columns(3)
    c1.metric("Monthly Expense (₹)", f"{monthly_expense_retirement:,.0f}")
    c2.metric("Monthly Pension (₹)", f"{monthly_pension:,.0f}")
    c3.metric("Monthly Gap (₹)", f"{max(0, monthly_expense_retirement - monthly_pension):,.0f}")

    # -------------------------------
    # BUCKET ALLOCATION (FIXED %)
    # -------------------------------
    b1 = total_corpus * 0.20
    b2 = total_corpus * 0.30
    b3 = total_corpus * 0.50

    crash_duration = 0
    if crash_years == "3 Years":
        crash_duration = 3
    elif crash_years == "5 Years":
        crash_duration = 5

    crash_impact = 0.15  # 15% per year on Bucket 3 only

    records = []

    retirement_years = life_expectancy - retirement_age

    for year in range(1, retirement_years + 1):

        infl = inflation + 0.04 if inflation_shock and year <= 5 else inflation
        annual_expense = annual_expense_base * ((1 + infl) ** (year - 1))
        annual_gap = max(0, annual_expense - annual_pension)

        # ---- Withdrawal (ONCE) ----
        withdrawal = min(b1, annual_gap)
        b1 -= withdrawal
        annual_gap -= withdrawal

        # ---- Refill only if needed ----
        if annual_gap > 0 and b2 > 0:
            refill = min(b2, annual_gap)
            b2 -= refill
            b1 += refill
            annual_gap -= refill

        if annual_gap > 0 and b3 > 0:
            refill = min(b3, annual_gap)
            b3 -= refill
            b1 += refill
            annual_gap -= refill

        # ---- Market Crash ----
        if year <= crash_duration:
            b3 *= (1 - crash_impact)

        # ---- Returns AFTER withdrawals ----
        b1 *= (1 + r1)
        b2 *= (1 + r2)
        b3 *= (1 + r3)

        total = b1 + b2 + b3

        records.append([
            retirement_age + year - 1,
            annual_expense / 12,
            b1, b2, b3, total
        ])

        if total <= 0:
            break

    df = pd.DataFrame(
        records,
        columns=[
            "Age",
            "Monthly Expense (Inflation Adjusted)",
            "Bucket 1",
            "Bucket 2",
            "Bucket 3",
            "Total Corpus"
        ]
    )

    # ---------------------------------
    # OUTPUT
    # ---------------------------------
    st.subheader("Retirement Cashflow & Corpus Evolution")
    st.dataframe(df, use_container_width=True)

    st.subheader("Bucket-wise Balances")
    st.line_chart(df.set_index("Age")[["Bucket 1", "Bucket 2", "Bucket 3"]])

    st.subheader("Monthly Expense Trend")
    st.line_chart(df.set_index("Age")[["Monthly Expense (Inflation Adjusted)"]])

    if df["Total Corpus"].iloc[-1] > 0:
        st.success("✅ Corpus sustains till life expectancy.")
    else:
        st.error(f"❌ Corpus exhausted at age {df['Age'].iloc[-1]}.")

    # ---------------------------------
    # DOWNLOAD
    # ---------------------------------
    buffer = BytesIO()
    df.to_excel(buffer, index=False)
    buffer.seek(0)

    st.download_button(
        "⬇ Download Excel Report",
        buffer,
        "Corrected_Retirement_Simulation.xlsx",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

st.caption("For education and capacity building only. Not financial advice.")
