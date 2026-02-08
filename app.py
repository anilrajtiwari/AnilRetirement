import streamlit as st
import pandas as pd
from io import BytesIO

# ---------------------------------
# PAGE SETUP
# ---------------------------------
st.set_page_config(page_title="PSU Retirement Simulator", layout="wide")
st.title("PSU Retirement Planning Simulator")
st.caption("Three-Bucket Strategy | Educational & Training Tool")

# ---------------------------------
# SIDEBAR INPUTS
# ---------------------------------
st.sidebar.header("Employee Inputs")

current_age = st.sidebar.number_input("Current Age", 40, 59, 55)
retirement_age = st.sidebar.number_input("Retirement Age", 55, 65, 60)
life_expectancy = st.sidebar.number_input("Life Expectancy", 70, 100, 85)

monthly_expense = st.sidebar.number_input("Current Monthly Expense (₹)", 10000, 300000, 75000)
inflation = st.sidebar.slider("Inflation Rate (%)", 3.0, 10.0, 6.0) / 100

monthly_pension = st.sidebar.number_input("Monthly Assured Pension (₹)", 0, 200000, 40000)
total_corpus = st.sidebar.number_input("Total Retirement Corpus (₹)", 1000000, 50000000, 11000000)

st.sidebar.subheader("Bucket Structure")
bucket1_years = st.sidebar.slider("Bucket 1 Duration (years)", 1, 5, 3)
bucket2_years = st.sidebar.slider("Bucket 2 Duration (years)", 3, 10, 7)

r1 = st.sidebar.slider("Bucket 1 Return (%)", 2.0, 7.0, 4.0) / 100
r2 = st.sidebar.slider("Bucket 2 Return (%)", 4.0, 9.0, 6.5) / 100
r3 = st.sidebar.slider("Bucket 3 Return (%)", 7.0, 12.0, 9.5) / 100

# ---------------------------------
# SCENARIO TOGGLES
# ---------------------------------
st.sidebar.subheader("Stress Test Scenarios")
market_crash = st.sidebar.checkbox("One-time Market Crash (Year 1)")
inflation_shock = st.sidebar.checkbox("High Inflation (First 5 Years)")

run = st.sidebar.button("Run Simulation")

# ---------------------------------
# MAIN LOGIC
# ---------------------------------
if run:
    retirement_years = life_expectancy - retirement_age

    base_expense = monthly_expense * 12
    annual_pension = monthly_pension * 12
    base_gap = max(0, base_expense - annual_pension)

    # Initial buckets
    bucket1 = base_gap * bucket1_years
    bucket2 = base_gap * bucket2_years
    bucket3 = total_corpus - (bucket1 + bucket2)

    b1, b2, b3 = bucket1, bucket2, bucket3

    crash_year = 1
    crash_impact = 0.30  # 30% one-time fall

    records = []

    for year in range(1, retirement_years + 1):

        # Inflation logic
        infl = inflation + 0.04 if inflation_shock and year <= 5 else inflation
        expense = base_expense * ((1 + infl) ** (year - 1))
        gap = max(0, expense - annual_pension)

        # Withdrawals only from Bucket 1
        withdrawal = min(b1, gap)
        b1 -= withdrawal
        gap -= withdrawal

        # Refill rules
        if b1 <= 0 and b2 > 0:
            refill = min(b2, base_gap * bucket1_years)
            b2 -= refill
            b1 += refill

        if b2 <= 0 and b3 > 0:
            refill = min(b3, base_gap * bucket2_years)
            b3 -= refill
            b2 += refill

        # Market crash (ONE TIME)
        if market_crash and year == crash_year:
            b3 *= (1 - crash_impact)

        # Apply returns
        b1 *= (1 + r1)
        b2 *= (1 + r2)
        b3 *= (1 + r3)

        total = b1 + b2 + b3

        records.append([
            year, expense, b1, b2, b3, total
        ])

        if total <= 0:
            break

    df = pd.DataFrame(
        records,
        columns=["Year", "Expense", "Bucket 1", "Bucket 2", "Bucket 3", "Total Corpus"]
    )

    # ---------------------------------
    # OUTPUTS
    # ---------------------------------
    st.subheader("Year-wise Simulation")
    st.dataframe(df, use_container_width=True)

    # ---------------------------------
    # CORRECT GRAPHS (FIXED)
    # ---------------------------------
    st.subheader("Bucket-wise Balances Over Time")

    st.line_chart(
        df.set_index("Year")[["Bucket 1", "Bucket 2", "Bucket 3"]]
    )

    st.subheader("Total Retirement Corpus")
    st.line_chart(
        df.set_index("Year")[["Total Corpus"]]
    )

    # ---------------------------------
    # RESULT MESSAGE
    # ---------------------------------
    if df["Total Corpus"].iloc[-1] > 0:
        st.success("✅ Corpus lasts for full retirement period")
    else:
        st.error(f"❌ Corpus exhausted in Year {df['Year'].iloc[-1]}")

    # ---------------------------------
    # DOWNLOAD EXCEL
    # ---------------------------------
    buffer = BytesIO()
    df.to_excel(buffer, index=False)
    buffer.seek(0)

    st.download_button(
        "⬇ Download Excel Report",
        buffer,
        "Retirement_Simulation.xlsx",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

st.caption("Disclaimer: For education & capacity building only. Not financial advice.")
