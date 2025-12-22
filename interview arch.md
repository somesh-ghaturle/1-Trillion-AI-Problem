flowchart TB

%% -----------------------------
%% Data Sources
%% -----------------------------
A[Enterprise Data Sources<br/>• Clinical Data<br/>• Finance Data<br/>• Ops Logs<br/>• Documents / PDFs] 

%% -----------------------------
%% ETL & Quality Layer
%% -----------------------------
subgraph Ingestion["Ingestion & Quality Control"]
    B[ETL & Ingestion Layer<br/>AWS Glue / Azure Data Factory]
    Qual[Data Quality Validator<br/>(data_quality_validator.py)<br/>• Schema & Anomaly Checks<br/>• PII Removal]
end

%% -----------------------------
%% Storage Layer
%% -----------------------------
C[Data Lake / Warehouse<br/>S3 / ADLS / Snowflake<br/>Versioned & Encrypted]

%% -----------------------------
%% Governance & Trust Layer
%% -----------------------------
subgraph Governance["Governance & Trust"]
    Gov[Data Governance Framework<br/>(data_governance.py)<br/>• Metric Definitions<br/>• Metadata Management]
    Trust[Trust Scoring Engine<brflowchart TB

%% -----------------------------
%% Data Sources
%% -----------------------------
A[Enterprise Data Sources<br/>• Clinical Data<br/>• Finance Data<br/>• Ops Logs<br/>• Documents / PDFs] 

%% -----------------------------
%% ETL & Quality Layer
%% -----------------------------
subgraph Ingestion["Ingestion & Quality Control"]
    B[ETL & Ingestion Layer<br/>AWS Glue / Azure Data Factory]
    Qual[Data Quality Validator<br/>(data_quality_validator.py)<br/>• Schema & Anomaly Checks<br/>• PII Removal]
end

%% -----------------------------
%% Storage Layer
%% -----------------------------
C[Data Lake / Warehouse<br/>S3 / ADLS / Snowflake<br/>Versioned & Encrypted]

%% -----------------------------
%% Governance & Trust Layer
%% -----------------------------
subgraph Governance["Governance & Trust"]
    Gov[Data Governance Framework<br/>(data_governance.py)<br/>• Metric Definitions<br/>• Metadata Management]
    Trust[Trust Scoring Engine<br