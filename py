# cleanlytics_mvp.py
import streamlit as st
import pandas as pd
import openai
import stripe
import os
from io import StringIO
import json

# ====== SETUP ======
# OpenAI API key (set as environment variable)
openai.api_key = os.getenv("OPENAI_API_KEY")

# Stripe API key (set as environment variable)
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")

st.title("Cleanlytics – AI Data Cleaning & Validation")
st.write("""
Upload a CSV/XLSX file, pay per file, and instantly get a **cleaned spreadsheet** 
and a **validation report**.
""")

# ====== FILE UPLOAD ======
uploaded_file = st.file_uploader("Upload CSV/XLSX file", type=["csv", "xlsx"])

def create_checkout_session(amount_cents, currency="usd"):
    session = stripe.checkout.Session.create(
        payment_method_types=['card'],
        line_items=[{
            'price_data': {
                'currency': currency,
                'product_data': {'name': 'Cleanlytics File Processing'},
                'unit_amount': amount_cents,
            },
            'quantity': 1,
        }],
        mode='payment',
        success_url="https://your-streamlit-url",  # Replace with your app URL
        cancel_url="https://your-streamlit-url",   # Replace with your app URL
    )
    return session.url

if uploaded_file:
    # Read CSV/XLSX
    if uploaded_file.name.endswith(".csv"):
        df = pd.read_csv(uploaded_file)
    else:
        df = pd.read_excel(uploaded_file)

    st.write("### Original Data Preview")
    st.dataframe(df.head())

    # ====== PAYMENT STEP ======
    st.write("Before processing, please complete payment.")

    checkout_url = create_checkout_session(1000)  # $10 per file
    st.markdown(f"[💳 Pay $10 to Clean This File]({checkout_url})", unsafe_allow_html=True)
    st.write("After payment, come back and click 'Process File' below.")

    if st.button("Process File (after payment)"):
        st.write("Processing your data... please wait.")

        # ====== AI CLEANING PROMPT ======
        table_str = df.to_csv(index=False)
        prompt = f"""
You are an AI data cleaning assistant.

Input Table (CSV format):
{table_str}

Tasks:
1. Detect missing values, duplicates, inconsistent formatting, and outliers.
2. Clean the table:
   - Remove duplicates
   - Standardize formatting (dates, currency, numbers, text capitalization)
   - Fill missing values if obvious
3. Produce:
   a) Cleaned CSV table
   b) Plain-language validation report:
      - Number of duplicates removed
      - Number of missing values corrected
      - Columns standardized
      - Outliers flagged (if any)
Return your response as a JSON object with two fields: "cleaned_csv" and "report".
"""

        # ====== CALL OPENAI ======
        try:
            response = openai.ChatCompletion.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0
            )
            ai_output = response['choices'][0]['message']['content']

            # ====== PARSE AI RESPONSE ======
            try:
                data = json.loads(ai_output)
                cleaned_csv_str = data["cleaned_csv"]
                report = data["report"]

                cleaned_df = pd.read_csv(StringIO(cleaned_csv_str))

                st.write("### Cleaned Data Preview")
                st.dataframe(cleaned_df.head())

                # ====== DOWNLOAD BUTTONS ======
                st.download_button(
                    label="Download Cleaned CSV",
                    data=cleaned_df.to_csv(index=False).encode("utf-8"),
                    file_name="cleaned_data.csv",
                    mime="text/csv"
                )

                st.download_button(
                    label="Download Validation Report",
                    data=report,
                    file_name="validation_report.txt",
                    mime="text/plain"
                )

            except Exception as e:
                st.error(f"Error parsing AI output: {e}")
                st.write("AI output was:", ai_output)

        except Exception as e:
            st.error(f"AI API call failed: {e}")