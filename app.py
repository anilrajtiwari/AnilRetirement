import streamlit as st
import pandas as pd
from io import BytesIO

# ---------------------------------
# PAGE SETUP
# ---------------------------------
st.set_page_config(page_title="PSU Retirement Simulator", layout="wide")
st.title("PSU Retirement Planning Simulator")
st.caption("Three-Bucket Strategy | Educational & Capacity Building Tool")

# ---------------------------------
# SIDEBAR INPUTS
# ---------------------------------
st.sidebar.header("Employee Inputs")

current_age = st.sidebar.number_input(
    "Current Age", min_value=30, value=55, step=1
)

retirement_age = st.sidebar.number_input(
    "Retirement Age", min_value=current_age + 1, value=60, step=1
)

life_expectancy = st.sidebar.number_input(
    "Life Expectancy", min_value=retirement_age + 1, value=85, step=1
)

monthly_expense_today = st.sidebar.number_input(
    "Current Monthly Expense (₹)",
    min_value=0,
    value=75000,
    step=5000
)

inflation = st.sidebar.slider(
    "Expected Inflation Rate (%)", 3.0, 12.0, 6.0
) / 100

monthly_pension = st.sidebar.number_input(
    "Monthly Assured Pension (₹)",
    min_value=0,
    value=40000,
    step=5000
)

total_corpus = st.sidebar.number_input(
    "Total Retirement Corpus (₹)",
    min_value=0,
    value=11000000,
    step=500000
)

st.sidebar.subheader("Bucket Structure")

bucket1_years = st.sidebar.slider(
    "Bucket 1 Duration (years)", 1, 6, 3
)

bucket2_years = st.sidebar.slider(
    "Bucket 2 Duration (years)", 3, 12, 7
)

r1 = st.sidebar.slider(
    "Bucket 1 Return (%)", 2.0, 7.0, 4.0
) / 100

r2 = st.sidebar.slider(
    "Bucket 2 Return (%)", 4.0, 9.0, 6.5
) / 100

r3 = st.sidebar.slider(
    "Bucket 3 Return (%)", 7.0, 14.0, 9.5
) / 100

# ---------------------------------
# SCENARIO TOGGLES
# ---------------------------------
st.sidebar.subheader("Stress Test Scenarios")

market_crash = st.sidebar.checkbox(
    "One-time Market Crash (30% in Year 1)"
)

inflation_shock = st.sidebar.checkbox(
    "High Inflation (+4%) in First 5 Years After Retirement"
)

run = st.sidebar.button("Run Simulation")

# ---------------------------------
# MAIN LOGIC
# ---------------------------------
if run:

    # Years to retirement
    years_to_retirement = retirement_age - current_age

    # Monthly expense at retirement (inflation adjusted)
    monthly_expense_at_retirement = (
        monthly_expense_today * ((1 + inflation) ** years_to_retirement)
    )

    monthly_gap_at_retirement = max(
        0, monthly_expense_at_retirement - monthly_pension
    )

    # ---------------------------------
    # DISPLAY RETIREMENT TRANSITION
    # ---------------------------------
    st.subheader(f"At the Time of Retirement (Age {retirement_age})")

    c1, c2, c3 = st.columns(3)
    c1.metric(
        "Monthly Expense at Retirement (₹)",
        f"{monthly_expense_at_retirement:,.0f}"
    )
    c2.metric(
        "Monthly Pension (₹)",
        f"{monthly_pension:,.0f}"
    )
    c3.metric(
        "Monthly Income Gap (₹)",
        f"{monthly_gap_at_retirement:,.0f}"
    )

    # ---------------------------------
    # ANNUALISE VALUES
    # ---------------------------------
    annual_expense_start = monthly_expense_at_retirement * 12
    annual_pension = monthly_pension * 12
    base_annual_gap = max(0, annual_expense_start - annual_pension)

    retirement_years = life_expectancy - retirement_age

    # ---------------------------------
    # INITIAL BUCKET ALLOCATION
    # ---------------------------------
    bucket1 = base_annual_gap * bucket1_years
    bucket2 = base_annual_gap * bucket2_years
    bucket3 = total_corpus - (bucket1 + bucket2)

    b1, b2, b3 = bucket1, bucket2, bucket3

    crash_year = 1
    crash_impact = 0.30

    records = []

    # ---------------------------------
    # YEAR-BY-YEAR SIMULATION
    # ---------------------------------
    for year in range(1, retirement_years + 1):

        # Inflation after retirement
        infl = inflation + 0.04 if inflation_shock and year <= 5 else inflation

        annual_expense = annual_expense_start * ((1 + infl) ** (year - 1))
        annual_gap = max(0, annual_expense - annual_pension)

        # Withdrawals from Bucket 1
        withdrawal = min(b1, annual_gap)
        b1 -= withdrawal
        annual_gap -= withdrawal

        # Refill logic
        if b1 <= 0 and b2 > 0:
            refill = min(b2, base_annual_gap * bucket1_years)
            b2 -= refill
            b1 += refill

        if b2 <= 0 and b3 > 0:
            refill = min(b3, base_annual_gap * bucket2_years)
            b3 -= refill
            b2 += refill

        # Market crash (one-time)
        if market_crash and year == crash_year:
            b3 *= (1 - crash_impact)

        # Apply returns
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
    # OUTPUTS
    # ---------------------------------
    st.subheader("Post-Retirement Expense & Corpus Evolution")
    st.dataframe(df, use_container_width=True)

    st.subheader("Bucket-wise Balances Over Time")
    st.line_chart(
        df.set_index("Age")[["Bucket 1", "Bucket 2", "Bucket 3"]]
    )

    st.subheader("Inflation-Adjusted Monthly Expense Over Retirement")
    st.line_chart(
        df.set_index("Age")[["Monthly Expense (Inflation Adjusted)"]]
    )

    # ---------------------------------
    # FINAL RESULT
    # ---------------------------------
    if df["Total Corpus"].iloc[-1] > 0:
        st.success("✅ Retirement corpus lasts through full retirement period.")
    else:
        st.error(
            f"❌ Corpus exhausted at age {df['Age'].iloc[-1]}."
        )

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

st.caption(
    "Disclaimer: For education & capacity building only. Not financial advice."
)
