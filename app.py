import streamlit as st
import pandas as pd
import numpy as np
from io import BytesIO
from reportlab.platypus import SimpleDocTemplate, Paragraph, Table
from reportlab.lib.styles import getSampleStyleSheet

# ---------------------------------
# PAGE SETUP
# ---------------------------------
st.set_page_config(page_title="Retirement Simulator", layout="wide")
st.title("PSU Retirement Planning Simulator")
st.caption("Three-Bucket Strategy | Training & Capacity Building Tool")

# ---------------------------------
# SIDEBAR INPUTS
# ---------------------------------
st.sidebar.header("Employee Inputs")

current_age = st.sidebar.number_input("Current Age", 40, 59, 55)
retirement_age = st.sidebar.number_input("Retirement Age", 55, 65, 60)
life_expectancy = st.sidebar.number_input("Life Expectancy", 70, 100, 85)

monthly_expense = st.sidebar.number_input("Current Monthly Expense (₹)", 10000, 300000, 75000)
inflation = st.sidebar.slider("Normal Inflation Rate (%)", 3.0, 10.0, 6.0) / 100

monthly_pension = st.sidebar.number_input("Monthly Pension (₹)", 0, 200000, 40000)
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

market_crash = st.sidebar.checkbox("Market Crash in First 2 Years")
inflation_shock = st.sidebar.checkbox("High Inflation Shock")

run = st.sidebar.button("Run Retirement Model")

# ---------------------------------
# MAIN LOGIC
# ---------------------------------
if run:
    retirement_years = life_expectancy - retirement_age

    base_annual_expense = monthly_expense * 12
    annual_pension = monthly_pension * 12
    base_gap = max(0, base_annual_expense - annual_pension)

    bucket1 = base_gap * bucket1_years
    bucket2 = base_gap * bucket2_years
    bucket3 = total_corpus - (bucket1 + bucket2)

    records = []
    b1, b2, b3 = bucket1, bucket2, bucket3

    for year in range(1, retirement_years + 1):

        # Inflation shock logic
        if inflation_shock and year <= 5:
            infl = inflation + 0.04
        else:
            infl = inflation

        expense = base_annual_expense * ((1 + infl) ** (year - 1))
        gap = max(0, expense - annual_pension)

        # Withdrawals
        withdraw = min(b1, gap)
        b1 -= withdraw
        gap -= withdraw

        if b1 <= 0 and b2 > 0:
            refill = min(b2, base_gap * bucket1_years)
            b2 -= refill
            b1 += refill

        if b2 <= 0 and b3 > 0:
            refill = min(b3, base_gap * bucket2_years)
            b3 -= refill
            b2 += refill

        # Market crash logic
        if market_crash and year <= 2:
            b3 *= 0.75  # 25% crash

        # Apply returns
        b1 *= (1 + r1)
        b2 *= (1 + r2)
        b3 *= (1 + r3)

        total_balance = b1 + b2 + b3

        records.append([year, expense, b1, b2, b3, total_balance])

        if total_balance <= 0:
            break

    df = pd.DataFrame(
        records,
        columns=["Year", "Expense", "Bucket 1", "Bucket 2", "Bucket 3", "Total Corpus"]
    )

    # ---------------------------------
    # DISPLAY
    # ---------------------------------
    st.subheader("Simulation Results")
    st.dataframe(df, use_container_width=True)

    st.subheader("Corpus Trend")
    st.area_chart(df.set_index("Year")[["Bucket 1", "Bucket 2", "Bucket 3"]])
    st.line_chart(df.set_index("Year")["Total Corpus"])

    if df["Total Corpus"].iloc[-1] > 0:
        st.success("✅ Corpus survives full retirement period")
    else:
        st.error(f"❌ Corpus exhausted in year {df['Year'].iloc[-1]}")

    # ---------------------------------
    # DOWNLOAD EXCEL
    # ---------------------------------
    excel_buffer = BytesIO()
    df.to_excel(excel_buffer, index=False)
    excel_buffer.seek(0)

    st.download_button(
        label="⬇ Download Excel Report",
        data=excel_buffer,
        file_name="Retirement_Simulation.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

    # ---------------------------------
    # DOWNLOAD PDF
    # ---------------------------------
    pdf_buffer = BytesIO()
    doc = SimpleDocTemplate(pdf_buffer)
    styles = getSampleStyleSheet()

    content = [
        Paragraph("<b>PSU Retirement Simulation Report</b>", styles["Title"]),
        Paragraph(f"Total Corpus: ₹ {total_corpus:,.0f}", styles["Normal"]),
        Paragraph(f"Market Crash Scenario: {'Yes' if market_crash else 'No'}", styles["Normal"]),
        Paragraph(f"Inflation Shock Scenario: {'Yes' if inflation_shock else 'No'}", styles["Normal"]),
    ]

    table_data = [df.columns.tolist()] + df.values.tolist()
    content.append(Table(table_data))

    doc.build(content)
    pdf_buffer.seek(0)

    st.download_button(
        label="⬇ Download PDF Report",
        data=pdf_buffer,
        file_name="Retirement_Simulation.pdf",
        mime="application/pdf"
    )

st.caption("Disclaimer: Educational use only. Not financial advice.")
