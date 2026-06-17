import streamlit as st
import pandas as pd
import os
from datetime import date
import plotly.express as px
from fpdf import FPDF

# ---------------------------------------------------------
# App Config
# ---------------------------------------------------------
st.set_page_config(page_title="FinMate AI", page_icon="💰", layout="wide")

DATA_DIR = "data"
TRANSACTIONS_FILE = os.path.join(DATA_DIR, "transactions.csv")
GOALS_FILE = os.path.join(DATA_DIR, "goals.csv")
os.makedirs(DATA_DIR, exist_ok=True)

CATEGORIES = {
    "Income": ["Salary", "Freelance", "Business", "Investment", "Other Income"],
    "Expense": ["Food", "Transport", "Shopping", "Bills", "Rent",
                "Entertainment", "Health", "Education", "Other Expense"],
}

# ---------------------------------------------------------
# Data Helpers
# ---------------------------------------------------------
def load_transactions():
    if os.path.exists(TRANSACTIONS_FILE):
        df = pd.read_csv(TRANSACTIONS_FILE, parse_dates=["date"])
    else:
        df = pd.DataFrame(columns=["date", "type", "category", "amount", "note"])
    return df


def save_transactions(df):
    df.to_csv(TRANSACTIONS_FILE, index=False)


def load_goals():
    if os.path.exists(GOALS_FILE):
        df = pd.read_csv(GOALS_FILE)
    else:
        df = pd.DataFrame(columns=["goal_name", "target_amount", "saved_amount", "deadline"])
    return df


def save_goals(df):
    df.to_csv(GOALS_FILE, index=False)


# ---------------------------------------------------------
# Sidebar Navigation
# ---------------------------------------------------------
st.sidebar.title("💰 FinMate AI")
st.sidebar.caption("Your AI-powered personal finance companion")
page = st.sidebar.radio(
    "Navigate",
    ["📊 Dashboard", "➕ Add Transaction", "🎯 Goals", "🧠 AI Insights", "📄 Reports"],
)

transactions = load_transactions()
goals = load_goals()

# ---------------------------------------------------------
# Dashboard
# ---------------------------------------------------------
if page == "📊 Dashboard":
    st.title("📊 Dashboard")

    if transactions.empty:
        st.info("No transactions yet. Add some from the 'Add Transaction' page to see your dashboard.")
    else:
        total_income = transactions.loc[transactions["type"] == "Income", "amount"].sum()
        total_expense = transactions.loc[transactions["type"] == "Expense", "amount"].sum()
        net_savings = total_income - total_expense

        col1, col2, col3 = st.columns(3)
        col1.metric("Total Income", f"Rs {total_income:,.0f}")
        col2.metric("Total Expense", f"Rs {total_expense:,.0f}")
        savings_pct = (net_savings / total_income * 100) if total_income > 0 else 0
        col3.metric("Net Savings", f"Rs {net_savings:,.0f}", delta=f"{savings_pct:.1f}% of income")

        st.divider()

        c1, c2 = st.columns(2)
        with c1:
            st.subheader("Expense by Category")
            expense_df = transactions[transactions["type"] == "Expense"]
            if not expense_df.empty:
                cat_sum = expense_df.groupby("category")["amount"].sum().reset_index()
                fig = px.pie(cat_sum, values="amount", names="category", hole=0.4)
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.write("No expenses recorded yet.")

        with c2:
            st.subheader("Monthly Trend")
            trend_df = transactions.copy()
            trend_df["month"] = trend_df["date"].dt.to_period("M").astype(str)
            monthly = trend_df.groupby(["month", "type"])["amount"].sum().reset_index()
            if not monthly.empty:
                fig2 = px.bar(monthly, x="month", y="amount", color="type", barmode="group")
                st.plotly_chart(fig2, use_container_width=True)
            else:
                st.write("No data yet.")

        st.divider()
        st.subheader("Recent Transactions")
        st.dataframe(
            transactions.sort_values("date", ascending=False).head(10),
            use_container_width=True,
        )

# ---------------------------------------------------------
# Add Transaction
# ---------------------------------------------------------
elif page == "➕ Add Transaction":
    st.title("➕ Add Transaction")

    with st.form("add_transaction_form", clear_on_submit=True):
        t_type = st.selectbox("Type", ["Income", "Expense"])
        category = st.selectbox("Category", CATEGORIES[t_type])
        amount = st.number_input("Amount (Rs)", min_value=0.0, step=100.0)
        t_date = st.date_input("Date", value=date.today())
        note = st.text_input("Note (optional)")
        submitted = st.form_submit_button("Add Transaction")

        if submitted:
            if amount <= 0:
                st.error("Please enter an amount greater than 0.")
            else:
                new_row = pd.DataFrame([{
                    "date": pd.to_datetime(t_date),
                    "type": t_type,
                    "category": category,
                    "amount": amount,
                    "note": note,
                }])
                transactions = pd.concat([transactions, new_row], ignore_index=True)
                save_transactions(transactions)
                st.success(f"{t_type} of Rs {amount:,.0f} added successfully!")

# ---------------------------------------------------------
# Goals
# ---------------------------------------------------------
elif page == "🎯 Goals":
    st.title("🎯 Savings Goals")

    with st.expander("➕ Add New Goal"):
        with st.form("add_goal_form", clear_on_submit=True):
            goal_name = st.text_input("Goal Name")
            target_amount = st.number_input("Target Amount (Rs)", min_value=0.0, step=1000.0)
            deadline = st.date_input("Deadline")
            goal_submit = st.form_submit_button("Create Goal")

            if goal_submit and goal_name:
                new_goal = pd.DataFrame([{
                    "goal_name": goal_name,
                    "target_amount": target_amount,
                    "saved_amount": 0,
                    "deadline": deadline,
                }])
                goals = pd.concat([goals, new_goal], ignore_index=True)
                save_goals(goals)
                st.success("Goal created!")

    st.divider()

    if goals.empty:
        st.info("No goals set yet. Create one above.")
    else:
        for idx, row in goals.iterrows():
            progress = min(row["saved_amount"] / row["target_amount"], 1.0) if row["target_amount"] > 0 else 0
            st.subheader(row["goal_name"])
            st.progress(progress)

            colA, colB, colC = st.columns(3)
            colA.write(f"Saved: Rs {row['saved_amount']:,.0f}")
            colB.write(f"Target: Rs {row['target_amount']:,.0f}")
            colC.write(f"Deadline: {row['deadline']}")

            add_amount = st.number_input(
                f"Add to '{row['goal_name']}'", min_value=0.0, step=500.0, key=f"goal_{idx}"
            )
            if st.button("Update Savings", key=f"btn_{idx}"):
                goals.at[idx, "saved_amount"] += add_amount
                save_goals(goals)
                st.rerun()
            st.divider()

# ---------------------------------------------------------
# AI Insights
# ---------------------------------------------------------
elif page == "🧠 AI Insights":
    st.title("🧠 AI Financial Insights")

    if transactions.empty:
        st.info("Add some transactions first to get AI-powered insights.")
    else:
        expense_df = transactions[transactions["type"] == "Expense"]
        income_df = transactions[transactions["type"] == "Income"]
        total_income = income_df["amount"].sum()
        total_expense = expense_df["amount"].sum()

        st.subheader("💡 Smart Suggestions")

        if not expense_df.empty:
            cat_totals = expense_df.groupby("category")["amount"].sum()
            top_category = cat_totals.idxmax()
            top_amount = cat_totals.max()
            top_pct = (top_amount / total_expense * 100) if total_expense > 0 else 0

            st.write(
                f"📌 Your highest spending category is **{top_category}**, making up "
                f"**{top_pct:.1f}%** of total expenses (Rs {top_amount:,.0f})."
            )

            if top_pct > 40:
                st.warning(
                    f"⚠️ {top_category} is consuming a large share of your budget. "
                    "Consider setting a monthly limit for this category."
                )

        savings_rate = ((total_income - total_expense) / total_income * 100) if total_income > 0 else 0
        st.write(f"💰 Your current savings rate is **{savings_rate:.1f}%** of your income.")

        if total_income > 0 and savings_rate < 20:
            st.warning("⚠️ Financial experts generally recommend saving at least 20% of your income. You're below this target.")
        elif savings_rate >= 20:
            st.success("✅ Great job! You're meeting a healthy savings rate.")

        st.divider()
        st.subheader("📈 Next Month Prediction")

        trend_df = transactions.copy()
        trend_df["month"] = trend_df["date"].dt.to_period("M").astype(str)
        monthly_expense = trend_df[trend_df["type"] == "Expense"].groupby("month")["amount"].sum()

        if len(monthly_expense) >= 2:
            avg_change = monthly_expense.diff().mean()
            predicted_next = monthly_expense.iloc[-1] + avg_change
            predicted_next = max(predicted_next, 0)
            st.write(f"Based on your recent trend, predicted expense for next month: **Rs {predicted_next:,.0f}**")
        else:
            st.write("Add at least 2 months of data to unlock a trend-based prediction.")

# ---------------------------------------------------------
# Reports
# ---------------------------------------------------------
elif page == "📄 Reports":
    st.title("📄 Financial Reports")

    if transactions.empty:
        st.info("No data available to generate a report yet.")
    else:
        total_income = transactions.loc[transactions["type"] == "Income", "amount"].sum()
        total_expense = transactions.loc[transactions["type"] == "Expense", "amount"].sum()
        net_savings = total_income - total_expense

        st.subheader("Summary")
        st.write(f"Total Income: Rs {total_income:,.0f}")
        st.write(f"Total Expense: Rs {total_expense:,.0f}")
        st.write(f"Net Savings: Rs {net_savings:,.0f}")

        csv_bytes = transactions.to_csv(index=False).encode("utf-8")
        st.download_button("⬇️ Download CSV Report", csv_bytes, "finmate_report.csv", "text/csv")

        if st.button("📄 Generate PDF Report"):
            pdf = FPDF()
            pdf.add_page()
            pdf.set_font("Arial", "B", 16)
            pdf.cell(0, 10, "FinMate AI - Financial Report", ln=True, align="C")
            pdf.set_font("Arial", "", 12)
            pdf.ln(10)
            pdf.cell(0, 10, f"Total Income: Rs {total_income:,.0f}", ln=True)
            pdf.cell(0, 10, f"Total Expense: Rs {total_expense:,.0f}", ln=True)
            pdf.cell(0, 10, f"Net Savings: Rs {net_savings:,.0f}", ln=True)
            pdf.ln(10)
            pdf.set_font("Arial", "B", 12)
            pdf.cell(0, 10, "Category-wise Breakdown:", ln=True)
            pdf.set_font("Arial", "", 11)

            cat_breakdown = transactions[transactions["type"] == "Expense"].groupby("category")["amount"].sum()
            for cat, amt in cat_breakdown.items():
                pdf.cell(0, 8, f"{cat}: Rs {amt:,.0f}", ln=True)

            pdf_bytes = bytes(pdf.output())
            st.download_button("⬇️ Download PDF", pdf_bytes, "finmate_report.pdf", "application/pdf")
