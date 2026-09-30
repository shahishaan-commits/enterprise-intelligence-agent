# Enterprise Intelligence Agent

A multi-source RAG application built on Databricks that ingests public enterprise filings, performs hybrid semantic retrieval across governed data, dynamically assembles grounded context, and uses foundation-model inference to produce source-backed analysis.

The current implementation analyzes public filings and earnings materials for Walmart, CVS Health, and Walgreens.

---

## Demo

![Enterprise Intelligence Agent demo](docs/demo-screenshot.png)

---

## What it does

The application lets a user ask natural-language questions such as:

- Compare Walmart, CVS Health, and Walgreens on revenue growth and profitability
- What has Walmart said about AI and automation?
- Which company is showing stronger operating leverage?
- What does management commentary suggest about future investment priorities?

The system retrieves relevant evidence from the underlying filings, injects that evidence into the model context, and generates a grounded response with source attribution.

---

## Architecture

```mermaid
flowchart TD
    A[Public Filings & Earnings Reports] --> B[Databricks Volume]
    B --> C[Delta Document Table]
    C --> D[Chunking + Metadata]
    D --> E[Delta Chunk Table]
    E --> F[Hybrid AI Search Index]
    F --> G[Metadata-Aware Retrieval]
    G --> H[RAG Context Assembly]
    H --> I[Databricks Foundation Model]
    I --> J[Streamlit Databricks App]
    J --> K[Grounded Analysis + Sources]
