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
    Trust[Trust Scoring Engine<br/>(trust_scoring.py)<br/>• Reliability Scores<br/>• Trust Levels]
end

%% -----------------------------
%% Dataset Prep
%% -----------------------------
D[Training Dataset Preparation<br/>Instruction → Input → Output]

E[RAG Dataset Preparation<br/>Document Chunking<br/>Embedding Generation]

%% -----------------------------
%% Fine-Tuning Layer
%% -----------------------------
F[Base LLM (Frozen)<br/>LLaMA / Mistral / Phi]

G[PEFT Fine-Tuning Layer<br/>LoRA / QLoRA]

H[Experiment Tracking & Model Registry<br/>MLflow / Azure ML Registry]

%% -----------------------------
%% Deployment
%% -----------------------------
I[Deployment Layer<br/>FastAPI + Docker]

J[Inference Runtime<br/>Optimized Serving]

%% -----------------------------
%% RAG Layer
%% -----------------------------
K[Vector Database<br/>FAISS / Pinecone]

L[RAG Orchestrator<br/>Retriever + Context Injection]

%% -----------------------------
%% Applications
%% -----------------------------
M[Secure API Gateway]

N[Applications & AI Agents<br/>Dashboards / Copilots]

%% -----------------------------
%% Flow Connections
%% -----------------------------
A --> B
B --> Qual
Qual --> C

C --> Trust
Trust --> D
Trust --> E

Gov -.-> C
Gov -.-> Trust

D --> F
F --> G
G --> H
H --> I
I --> J

E --> K
K --> L
L --> J

J --> M
M --> N
