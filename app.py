import streamlit as st
import pandas as pd
from io import BytesIO

# ---------------------------------
# PAGE CONFIG
# ---------------------------------
st.set_page_config(page_title="Anil's Retirement Simulator", layout="wide")
st.title("Anil's Retirement Planning Simulator")
st.caption("Three-Bucket Strategy | Stress Tested | Training Grade Model")

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
    "Total Retirement Corpus (₹)", 0, 200000000, 11000000, step=500000
)

st.sidebar.subheader("Expected Returns")
r1 = st.sidebar.slider("Bucket 1 (Cash) Return (%)", 2.0, 6.0, 4.0) / 100
r2 = st.sidebar.slider("Bucket 2 (Debt) Return (%)", 4.0, 8.0, 6.0) / 100
r3 = st.sidebar.slider("Bucket 3 (Growth) Return (%)", 7.0, 12.0, 9.0) / 100

st.sidebar.subheader("Stress Scenarios")
crash_option = st.sidebar.selectbox("Market Crash Duration", ["No Crash", "3 Years", "5 Years"])
inflation_shock = st.sidebar.checkbox("High Inflation (+4%) for First 5 Years After Retirement")

run = st.sidebar.button("Run Simulation")

# ---------------------------------
# RUN SIMULATION
# ---------------------------------
if run:

    years_to_retirement = retirement_age - current_age
    retirement_years = life_expectancy - retirement_age

    # Expense at retirement
    monthly_expense_retirement = monthly_expense_today * ((1 + inflation) ** years_to_retirement)
    annual_expense_base = monthly_expense_retirement * 12
    annual_pension = monthly_pension * 12

    # ---------------------------------
    # RETIREMENT SUMMARY PANEL
    # ---------------------------------
    st.subheader(f"Position at Retirement (Age {retirement_age})")

    monthly_gap = monthly_expense_retirement - monthly_pension

    col1, col2, col3 = st.columns(3)
    col1.metric("Monthly Expense at Retirement (₹)", f"{monthly_expense_retirement:,.0f}")
    col2.metric("Monthly Pension (₹)", f"{monthly_pension:,.0f}")

    if monthly_gap > 0:
        col3.metric("Monthly Shortfall (₹)", f"{monthly_gap:,.0f}", delta="Deficit", delta_color="inverse")
    else:
        col3.metric("Monthly Surplus (₹)", f"{abs(monthly_gap):,.0f}", delta="Surplus", delta_color="normal")

    # ---------------------------------
    # INITIAL BUCKET STRUCTURE
    # ---------------------------------
    bucket1_target = annual_expense_base * 3
    remaining = total_corpus - bucket1_target

    if remaining < 0:
        bucket1_target = total_corpus
        remaining = 0

    b1 = bucket1_target
    b2 = remaining * 0.50
    b3 = remaining * 0.50

    crash_years = 0
    if crash_option == "3 Years":
        crash_years = 3
    elif crash_option == "5 Years":
        crash_years = 5

    crash_impact = 0.20

    records = []
    exhaustion_age = None

    # ---------------------------------
    # YEAR LOOP
    # ---------------------------------
    for year in range(1, retirement_years + 1):

        effective_inflation = inflation
        if inflation_shock and year <= 5:
            effective_inflation += 0.04

        annual_expense = annual_expense_base * ((1 + effective_inflation) ** (year - 1))

        # Net cashflow
        net_cashflow = annual_pension - annual_expense

        if net_cashflow >= 0:
            b1 += net_cashflow
        else:
            annual_gap = abs(net_cashflow)

            withdraw_b1 = min(b1, annual_gap)
            b1 -= withdraw_b1
            annual_gap -= withdraw_b1

            if annual_gap > 0:
                withdraw_b2 = min(b2, annual_gap)
                b2 -= withdraw_b2
                annual_gap -= withdraw_b2

        # Market crash
        if year <= crash_years:
            b3 *= (1 - crash_impact)

        # Apply returns
        b1 *= (1 + r1)
        b2 *= (1 + r2)
        b3 *= (1 + r3)

        # Rebalancing every 3 years
        if year % 3 == 0:

            # Refill Bucket 1 ONLY from Bucket 2
            refill_b1 = max(0, bucket1_target - b1)
            transfer_from_b2 = min(b2, refill_b1)
            b2 -= transfer_from_b2
            b1 += transfer_from_b2

            # Refill Bucket 2 ONLY from Bucket 3
            desired_b2 = (b2 + b3) * 0.50
            refill_b2 = max(0, desired_b2 - b2)
            transfer_from_b3 = min(b3, refill_b2)
            b3 -= transfer_from_b3
            b2 += transfer_from_b3

        total_current = b1 + b2 + b3
        age = retirement_age + year - 1

        records.append([
            age,
            annual_expense / 12,
            b1,
            b2,
            b3,
            total_current
        ])

        if total_current <= 0 and exhaustion_age is None:
            exhaustion_age = age
            break

    df = pd.DataFrame(records, columns=[
        "Age",
        "Monthly Expense (Inflation Adjusted)",
        "Bucket 1",
        "Bucket 2",
        "Bucket 3",
        "Total Corpus"
    ])

    # ---------------------------------
    # RETIREMENT SCORE
    # ---------------------------------
    if exhaustion_age is None:
        status = "GREEN"
    elif exhaustion_age >= life_expectancy - 3:
        status = "AMBER"
    else:
        status = "RED"

    st.subheader("Retirement Health Analysis")

    if status == "GREEN":
        st.success("🟢 Sustainable till life expectancy.")
    elif status == "AMBER":
        st.warning("🟠 Marginal — Improvement Recommended.")
    else:
        st.error("🔴 Corpus exhausted before life expectancy.")

    st.markdown(f"""
**Life Expectancy:** {life_expectancy}  
**Corpus Exhaustion Age:** {exhaustion_age if exhaustion_age else "Not Exhausted"}  
**Retirement Score:** {status}
""")

    # Additional corpus recommendation
    if exhaustion_age:
        remaining_years = life_expectancy - exhaustion_age
        avg_annual_gap = max(0, annual_expense_base - annual_pension)
        additional_needed = avg_annual_gap * remaining_years
        st.markdown(f"### Suggested Additional Corpus: ₹{additional_needed:,.0f}")

    # ---------------------------------
    # CHARTS
    # ---------------------------------
    st.subheader("Bucket Trend")
    st.line_chart(df.set_index("Age")[["Bucket 1", "Bucket 2", "Bucket 3"]])

    st.subheader("Expense Trend")
    st.line_chart(df.set_index("Age")[["Monthly Expense (Inflation Adjusted)"]])

    st.subheader("Year-wise Projection Table")
    st.dataframe(df, use_container_width=True)

    # ---------------------------------
    # DOWNLOAD
    # ---------------------------------
    output = BytesIO()
    df.to_excel(output, index=False)
    output.seek(0)

    st.download_button(
        "Download Projection (Excel)",
        output,
        "PSU_Retirement_Projection.xlsx",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

st.caption("For training and educational purposes only. Not financial advice.")
