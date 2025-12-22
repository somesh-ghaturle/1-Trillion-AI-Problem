flowchart TB

%% -----------------------------
%% Data Sources
%% -----------------------------
A[Enterprise Data Sources<br/>• Clinical Data<br/>• Finance Data<br/>• Ops Logs<br/>• Documents / PDFs] 

%% -----------------------------
%% ETL Layer
%% -----------------------------
B[ETL & Ingestion Layer<br/>AWS Glue / Azure Data Factory<br/>Spark Jobs<br/>PII Removal & Validation]

%% -----------------------------
%% Storage Layer
%% -----------------------------
C[Data Lake / Warehouse<br/>S3 / ADLS / Snowflake<br/>Versioned & Encrypted]

%% -----------------------------
%% Dataset Prep
%% -----------------------------
D[Training Dataset Preparation<br/>Instruction → Input → Output<br/>De-identified & Labeled]

E[RAG Dataset Preparation<br/>Document Chunking<br/>Embedding Generation]

%% -----------------------------
%% Fine-Tuning Layer
%% -----------------------------
F[Base LLM (Frozen)<br/>LLaMA / Mistral / Phi]

G[PEFT Fine-Tuning Layer<br/>LoRA / QLoRA / Instruction Tuning]

H[Experiment Tracking & Model Registry<br/>MLflow / Azure ML Registry]

%% -----------------------------
%% Deployment
%% -----------------------------
I[Deployment Layer<br/>FastAPI + Docker<br/>Azure ML / SageMaker Endpoint]

J[Inference Runtime<br/>Optimized Serving<br/>Quantization / Autoscaling]

%% -----------------------------
%% RAG Layer
%% -----------------------------
K[Vector Database<br/>FAISS / Pinecone / Azure AI Search]

L[RAG Orchestrator<br/>Retriever + Context Injection]

%% -----------------------------
%% Applications
%% -----------------------------
M[Secure API Gateway<br/>Auth / RBAC / Logging]

N[Applications & AI Agents<br/>Dashboards<br/>Copilots<br/>Analytics Agents]

%% -----------------------------
%% Flow Connections
%% -----------------------------
A --> B
B --> C
C --> D
C --> E

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
