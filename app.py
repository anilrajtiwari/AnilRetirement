import streamlit as st
import pandas as pd
from io import BytesIO

# ---------------------------------
# PAGE SETUP
# ---------------------------------
st.set_page_config(page_title="PSU Retirement Simulator", layout="wide")
st.title("PSU Retirement Planning Simulator")
st.caption("Three-Bucket Strategy | Corrected & Audit-Safe Model")

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
    # BUCKET ALLOCATION
    # ---------------------------------
    b1 = total_corpus * 0.20
    b2 = total_corpus * 0.30
    b3 = total_corpus * 0.50

    crash_duration = 0
    if crash_years == "3 Years":
        crash_duration = 3
    elif crash_years == "5 Years":
        crash_duration = 5

    crash_impact = 0.15
    retirement_years = life_expectancy - retirement_age
    records = []

    exhaustion_age = None

    for year in range(1, retirement_years + 1):

        infl = inflation + 0.04 if inflation_shock and year <= 5 else inflation
        annual_expense = annual_expense_base * ((1 + infl) ** (year - 1))
        annual_gap = max(0, annual_expense - annual_pension)

        # Withdrawals
        withdraw = min(b1, annual_gap)
        b1 -= withdraw
        annual_gap -= withdraw

        if annual_gap > 0 and b2 > 0:
            refill = min(b2, annual_gap)
            b2 -= refill
            annual_gap -= refill

        if annual_gap > 0 and b3 > 0:
            refill = min(b3, annual_gap)
            b3 -= refill
            annual_gap -= refill

        # Market crash
        if year <= crash_duration:
            b3 *= (1 - crash_impact)

        # Growth
        b1 *= (1 + r1)
        b2 *= (1 + r2)
        b3 *= (1 + r3)

        total = b1 + b2 + b3
        age = retirement_age + year - 1

        records.append([age, annual_expense / 12, b1, b2, b3, total])

        if total <= 0 and exhaustion_age is None:
            exhaustion_age = age
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
    # TRAFFIC LIGHT SCORE
    # ---------------------------------
    if exhaustion_age is None:
        status = "GREEN"
    elif exhaustion_age >= life_expectancy - 3:
        status = "AMBER"
    else:
        status = "RED"

    # ---------------------------------
    # RECOMMENDATION LOGIC (DEFENSIVE)
    # ---------------------------------
    avg_annual_gap = max(
        0,
        (df["Monthly Expense (Inflation Adjusted)"].mean() * 12) - annual_pension
    )

    additional_corpus_needed = 0
    if exhaustion_age:
        shortfall_years = life_expectancy - exhaustion_age
        additional_corpus_needed = avg_annual_gap * shortfall_years

    # ---------------------------------
    # RETIREMENT HEALTH PANEL
    # ---------------------------------
    st.subheader("🧭 Retirement Health Analysis")

    if status == "GREEN":
        st.success("🟢 Retirement plan is sustainable till life expectancy.")
    elif status == "AMBER":
        st.warning("🟠 Retirement plan is marginally sufficient.")
    else:
        st.error("🔴 Retirement plan is NOT sustainable under current assumptions.")

    st.markdown(f"""
**Summary**
- Life Expectancy: **{life_expectancy}**
- Corpus Exhaustion Age: **{exhaustion_age if exhaustion_age else 'Not Exhausted'}**
- Retirement Health Score: **{status}**
""")

    if status != "GREEN":
        st.markdown("### What Went Wrong")
        st.markdown("""
- Retirement expenses grow every year due to inflation  
- Pension income remains fixed and loses purchasing power  
- Corpus is drawn down faster in early retirement  
- Market shocks reduce compounding potential  
""")

        st.markdown("### What You Can Do")
        st.markdown(f"""
- Increase retirement corpus by **~₹{additional_corpus_needed:,.0f}**  
- Delay retirement by 1–3 years to boost corpus and reduce drawdown  
- Reduce early retirement expenses  
- Add inflation-linked income sources  
""")

    # ---------------------------------
    # OUTPUT TABLES & CHARTS
    # ---------------------------------
    st.subheader("Year-wise Retirement Projection")
    st.dataframe(df, use_container_width=True)

    st.subheader("Bucket-wise Corpus Trend")
    st.line_chart(df.set_index("Age")[["Bucket 1", "Bucket 2", "Bucket 3"]])

    st.subheader("Inflation-Adjusted Monthly Expense Trend")
    st.line_chart(df.set_index("Age")[["Monthly Expense (Inflation Adjusted)"]])

    # ---------------------------------
    # EXCEL DOWNLOAD (FIXED ENGINE)
    # ---------------------------------
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, sheet_name="Projection", index=False)

        analysis_df = pd.DataFrame({
            "Metric": [
                "Life Expectancy",
                "Corpus Exhaustion Age",
                "Retirement Health Score",
                "Estimated Additional Corpus Required"
            ],
            "Value": [
                life_expectancy,
                exhaustion_age if exhaustion_age else "Not Exhausted",
                status,
                f"₹{additional_corpus_needed:,.0f}"
            ]
        })

        analysis_df.to_excel(writer, sheet_name="Retirement Analysis", index=False)

    output.seek(0)

    st.download_button(
        "⬇ Download Complete Retirement Report (Excel)",
        output,
        "PSU_Retirement_Analysis.xlsx",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

st.caption("For education and capacity building only. Not financial advice.")
