import os
import streamlit as st
from databricks.sdk import WorkspaceClient
from databricks.sdk.service.sql import StatementParameterListItem

# -----------------------------
# Page setup
# -----------------------------
st.set_page_config(
    page_title="Enterprise Intelligence Agent",
    page_icon="🧠",
    layout="wide"
)

st.title("Enterprise Intelligence Agent")

st.caption(
    "Grounded analysis across Walmart, CVS Health, and Walgreens "
    "using public filings, earnings reports, and AI-powered retrieval."
)

# -----------------------------
# Databricks client + resources
# -----------------------------
w = WorkspaceClient()

INDEX_NAME = os.getenv(
    "VECTOR_SEARCH_INDEX",
    "workspace.default.enterprise_chunks_index"
)

WAREHOUSE_ID = os.getenv("WAREHOUSE_ID")

# -----------------------------
# User input
# -----------------------------
question = st.text_input(
    "Ask a question",
    placeholder="Compare Walmart, CVS Health, and Walgreens on AI investment."
)

# -----------------------------
# Run analysis
# -----------------------------
if st.button("Analyze", type="primary") and question:

    if not WAREHOUSE_ID:
        st.error("SQL warehouse resource is not configured for the app.")
        st.stop()

    # -------------------------
# Retrieval
# -------------------------
with st.spinner("Retrieving evidence..."):

    financial_terms = [
        "revenue",
        "sales",
        "profit",
        "profitability",
        "margin",
        "operating income",
        "earnings",
        "eps",
        "balance sheet",
        "cash flow",
        "debt",
        "guidance",
        "outlook",
        "financial",
        "valuation"
    ]

    question_lower = question.lower()
    is_financial_question = any(
        term in question_lower for term in financial_terms
    )

    companies = [
        "Walmart",
        "CVS Health",
        "Walgreens"
    ]

    rows = []

    for company in companies:

        company_query = f"""
        {company}: {question}
        """

        try:
            results = w.vector_search_indexes.query_index(
                index_name=INDEX_NAME,
                query_text=company_query,
                num_results=8,
                columns=[
                    "company",
                    "document_type",
                    "source",
                    "page",
                    "text"
                ]
            )

        except Exception as e:
            st.error(f"Vector search failed for {company}: {e}")
            st.stop()

        if (
            results
            and results.result
            and results.result.data_array
        ):

            company_rows = []

            for row in results.result.data_array:

                row_company = str(row[0])
                document_type = str(row[1])

                # Only keep evidence belonging to the company
                if row_company != company:
                    continue

                # For financial questions, prefer primary financial documents
                if is_financial_question:
                    preferred_types = [
                        "10-K",
                        "10-Q",
                        "Annual Report",
                        "Earnings Release"
                    ]

                    if document_type in preferred_types:
                        company_rows.append(row)

                else:
                    company_rows.append(row)

            # Fallback:
            # if financial filtering removed everything,
            # keep the company's general retrieval results
            if not company_rows:
                for row in results.result.data_array:
                    if str(row[0]) == company:
                        company_rows.append(row)

            # Keep only the strongest few chunks per company
            rows.extend(company_rows[:4])

    if not rows:
        st.warning("No relevant evidence was found.")
        st.stop()

    # Build augmentation context
    context_blocks = []

    for row in rows:
        company = row[0]
        document_type = row[1]
        source = row[2]
        page = row[3]
        text = row[4]

        context_blocks.append(
            f"""
COMPANY: {company}
DOCUMENT TYPE: {document_type}
SOURCE: {source}
PAGE: {page}

{text}
"""
        )

    context = "\n\n---\n\n".join(context_blocks)

    # -------------------------
    # Augmentation + Generation
    # -------------------------
    with st.spinner("Generating grounded answer..."):

        prompt = f"""
You are an enterprise intelligence analyst.

Answer the user's question using ONLY the retrieved evidence provided below.

Formatting rules:
- Return valid Markdown.
- Use clear section headings.
- Use bullet points for comparisons.
- Put each company name in bold.
- Keep source citations at the end of each bullet.
- Do not use tables unless the question clearly benefits from one.
- Do not invent facts.
- If evidence is insufficient, say so explicitly.
- Keep financial figures readable and separated with spaces.
- Do not use raw LaTeX or mathematical notation.
- Render currency as plain text such as USD 706.4 billion; do not use LaTeX or mathematical formatting.

USER QUESTION:
{question}

RETRIEVED EVIDENCE:
{context}
"""

        try:
            response = w.statement_execution.execute_statement(
                warehouse_id=WAREHOUSE_ID,
                statement="SELECT ai_gen(:prompt) AS answer",
                parameters=[
                    StatementParameterListItem(
                        name="prompt",
                        value=prompt
                    )
                ],
                wait_timeout="50s"
            )
        except Exception as e:
            st.error(f"Generation failed: {e}")
            st.stop()

        answer = None

        if (
            response
            and response.result
            and response.result.data_array
            and len(response.result.data_array) > 0
        ):
            answer = response.result.data_array[0][0]

        if not answer:
            st.error("The model did not return an answer.")
            st.stop()

    # -------------------------
    # Output
    # -------------------------
    st.subheader("Analysis")
    st.markdown(answer)

    st.subheader("Sources used")

    seen = set()

    for row in rows:
        company = row[0]
        document_type = row[1]
        source = row[2]
        page = row[3]

        key = (source, page)

        if key not in seen:
            seen.add(key)

            st.markdown(
                f"• **{company}** — {source}, page {page}"
            )