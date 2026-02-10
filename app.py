import streamlit as st
import pandas as pd
from io import BytesIO

# ---------------------------------
# PAGE SETUP
# ---------------------------------
st.set_page_config(page_title="Anil's Retirement Simulator", layout="wide")
st.title("Anil's Retirement Planning Simulator")
st.caption("Three-Bucket Strategy | Strict 3-Year Refill Discipline")

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
    "Total Retirement Corpus (₹)", 0, 100000000, 11000000, step=500000
)

st.sidebar.subheader("Expected Returns")
r1 = st.sidebar.slider("Bucket 1 (Cash) Return (%)", 2.0, 6.0, 4.0) / 100
r2 = st.sidebar.slider("Bucket 2 (Debt) Return (%)", 4.0, 8.0, 6.0) / 100
r3 = st.sidebar.slider("Bucket 3 (Growth) Return (%)", 7.0, 12.0, 9.0) / 100

st.sidebar.subheader("Stress Scenarios")
crash_years = st.sidebar.selectbox("Market Crash Duration", ["No Crash", "3 Years", "5 Years"])
inflation_shock = st.sidebar.checkbox("High Inflation (+4%) for First 5 Years After Retirement")

run = st.sidebar.button("Run Simulation")

# ---------------------------------
# MAIN LOGIC
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
    c3.metric("Monthly Income Gap (₹)", f"{max(0, monthly_expense_retirement - monthly_pension):,.0f}")

    # ---------------------------------
    # INITIAL BUCKET SETUP
    # ---------------------------------
    bucket1_target = annual_expense_base * 3

    if total_corpus <= bucket1_target:
        b1, b2, b3 = total_corpus, 0, 0
    else:
        b1 = bucket1_target
        remaining = total_corpus - bucket1_target
        b2 = remaining * 0.50
        b3 = remaining * 0.50

    crash_duration = 3 if crash_years == "3 Years" else 5 if crash_years == "5 Years" else 0
    crash_impact = 0.15

    retirement_years = life_expectancy - retirement_age
    records = []
    exhaustion_age = None

    # ---------------------------------
    # SIMULATION LOOP
    # ---------------------------------
    for year in range(1, retirement_years + 1):

        infl = inflation + 0.04 if inflation_shock and year <= 5 else inflation
        annual_expense = annual_expense_base * ((1 + infl) ** (year - 1))
        annual_gap = max(0, annual_expense - annual_pension)

        # ---------------------------------
        # EXPENSE WITHDRAWAL (STRICT)
        # ---------------------------------
        withdraw = min(b1, annual_gap)
        b1 -= withdraw
        annual_gap -= withdraw

        if annual_gap > 0 and b2 > 0:
            used = min(b2, annual_gap)
            b2 -= used
            annual_gap -= used

        # ❌ Bucket 3 NEVER used for expenses

        # ---------------------------------
        # SCHEDULED REFILL EVERY 3 YEARS
        # ---------------------------------
        if year % 3 == 0:

            # Refill Bucket 1 ONLY from Bucket 2
            refill_b1 = max(0, bucket1_target - b1)
            from_b2 = min(b2, refill_b1)
            b2 -= from_b2
            b1 += from_b2

            # Refill Bucket 2 ONLY from Bucket 3
            target_b2 = (total_corpus - bucket1_target) * 0.50
            refill_b2 = max(0, target_b2 - b2)
            from_b3 = min(b3, refill_b2)
            b3 -= from_b3
            b2 += from_b3

        # ---------------------------------
        # MARKET CRASH (ONLY BUCKET 3)
        # ---------------------------------
        if year <= crash_duration:
            b3 *= (1 - crash_impact)

        # ---------------------------------
        # ANNUAL RETURNS
        # ---------------------------------
        b1 *= (1 + r1)
        b2 *= (1 + r2)
        b3 *= (1 + r3)

        total = b1 + b2 + b3
        age = retirement_age + year - 1

        records.append([age, annual_expense / 12, b1, b2, b3, total])

        if total <= 0 and exhaustion_age is None:
            exhaustion_age = age
            break

    # ---------------------------------
    # RESULTS
    # ---------------------------------
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

    if exhaustion_age is None:
        status = "GREEN"
    elif exhaustion_age >= life_expectancy - 3:
        status = "AMBER"
    else:
        status = "RED"

    st.subheader("🧭 Retirement Health Analysis")

    if status == "GREEN":
        st.success("🟢 Retirement plan is sustainable till life expectancy.")
    elif status == "AMBER":
        st.warning("🟠 Retirement plan is marginally sufficient.")
    else:
        st.error("🔴 Retirement plan is NOT sustainable.")

    st.markdown(f"""
**Summary**
- Life Expectancy: **{life_expectancy}**
- Corpus Exhaustion Age: **{exhaustion_age if exhaustion_age else 'Not Exhausted'}**
- Retirement Health Score: **{status}**
""")

    # ---------------------------------
    # OUTPUTS
    # ---------------------------------
    st.subheader("Year-wise Retirement Projection")
    st.dataframe(df, use_container_width=True)

    st.subheader("Bucket-wise Corpus Trend")
    st.line_chart(df.set_index("Age")[["Bucket 1", "Bucket 2", "Bucket 3"]])

    st.subheader("Inflation-Adjusted Monthly Expense Trend")
    st.line_chart(df.set_index("Age")[["Monthly Expense (Inflation Adjusted)"]])

    # ---------------------------------
    # EXCEL DOWNLOAD
    # ---------------------------------
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, sheet_name="Projection", index=False)

    output.seek(0)
    st.download_button(
        "⬇ Download Retirement Projection (Excel)",
        output,
        "PSU_Retirement_Projection.xlsx",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

st.caption("For education and capacity building only. Not financial advice.")
