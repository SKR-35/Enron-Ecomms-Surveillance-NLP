# Methodology

## Overview

This project builds an end-to-end email communications surveillance pipeline using the Enron Email Dataset.

The objective is to identify potentially risky communications using a combination of:

* Email parsing
* Natural language processing (NLP)
* Communication network analytics
* Risk phrase detection
* Risk scoring
* Interactive investigation dashboards

The project follows a surveillance-oriented workflow commonly used in compliance, fraud, AML, FCC and investigation environments.

---

# Dataset

## Source

Enron Email Dataset

The dataset contains over 500,000 corporate emails exchanged among Enron employees.

## Initial Structure

Raw data consisted of:

| Column  | Description                 |
| ------- | --------------------------- |
| file    | Original email file path    |
| message | Raw RFC-style email message |

Total records:

* 517,401 emails

---

# Pipeline Architecture

```text
Raw Emails
    ↓
Email Parsing
    ↓
Text Feature Engineering
    ↓
Risk Phrase Detection
    ↓
Network Edge Construction
    ↓
Network Metrics
    ↓
Risk Scoring
    ↓
Dashboard Data Layer
```

---

# Email Parsing

Raw email messages were parsed into structured fields.

Extracted fields include:

* Message-ID
* Date
* From
* To
* Cc
* Bcc
* Subject
* X-Folder
* X-Origin
* Email Body

Results:

* 517,401 parsed emails
* 12 parsing errors
* Parsing success rate > 99.99%

---

# Text Feature Engineering

Several lightweight NLP features were generated.

Examples:

* Subject length
* Body length
* Word count
* Sentence count
* Reply detection
* Forward detection
* Attachment reference detection
* Uppercase ratio
* Exclamation count
* Question mark count

These features support downstream surveillance scoring.

---

# Risk Phrase Detection

A rule-based surveillance dictionary was created.

Categories include:

## Confidentiality

Examples:

* confidential
* strictly confidential
* privileged
* internal use only

## Concealment

Examples:

* keep this between us
* off the record
* do not tell
* hide

## Deletion

Examples:

* delete this
* destroy
* erase

## Legal & Regulatory

Examples:

* compliance
* regulator
* investigation
* subpoena
* audit

## Financial Risk

Examples:

* fraud
* manipulate
* bankruptcy
* default

## Urgency & Pressure

Examples:

* urgent
* ASAP
* immediately

## Offline Communication

Examples:

* call me
* discuss offline
* not by email

Each category contributes to an email-level risk phrase score.

---

# Communication Network Construction

A directed communication graph was built.

Node:

* Email address

Edge:

* Sender → Recipient

Network statistics:

* ~25,600 nodes
* ~309,000 directed communication edges

Edge attributes:

* Email count
* Risk phrase count
* Risk phrase percentage
* Average message size

---

# Network Analytics

The following graph metrics were calculated:

## Activity Metrics

* In-degree
* Out-degree
* Weighted email volume
* Total connections

## Centrality Metrics

* Degree Centrality
* In-Degree Centrality
* Out-Degree Centrality
* Betweenness Centrality

These metrics help identify:

* Key communicators
* Influential actors
* Information brokers
* Potential communication hubs

---

# Risk Scoring Methodology

A composite surveillance score was created.

The score combines:

| Component            | Weight |
| -------------------- | ------ |
| Risk Phrase Score    | 40%    |
| Network Volume       | 20%    |
| Network Betweenness  | 20%    |
| Sender Risk Activity | 10%    |
| Text Intensity       | 10%    |

Final score range:

* 0–100

Risk bands:

| Band   | Score |
| ------ | ----- |
| Low    | < 40  |
| Medium | 40–74 |
| High   | ≥ 75  |

---

# Dashboard Data Layer

The final pipeline exports dashboard-ready datasets.

Generated outputs include:

* Email investigation table
* Network node table
* Network edge table
* KPI summary
* Risk band summary
* Monthly activity summary

The dashboard layer is intentionally separated from the processing layer to improve performance and maintainability.

---

# Testing

Pipeline quality is validated through automated tests.

Coverage includes:

* Email parsing validation
* Network analytics validation
* Risk scoring validation
* End-to-end pipeline integrity checks

Current status:

* 11 tests passed

---

# Limitations

This project is intended as a surveillance analytics demonstration.

Limitations include:

* Rule-based risk phrase detection
* No supervised risk labels
* Approximate network centrality calculations
* Historical public dataset

Future improvements:

* Topic Modeling
* BERTopic
* Sentence Transformers
* BERT-based classification
* Community Detection
* LLM-assisted investigation summaries

---

# Conclusion

The project demonstrates an end-to-end communications surveillance workflow combining NLP, network analytics, risk scoring, testing and dashboard-ready outputs.

The resulting platform provides a realistic example of compliance and investigation analytics commonly used in financial crime, fraud and regulatory monitoring environments.