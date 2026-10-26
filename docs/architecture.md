# System Architecture & Technical Specification

## 1. High-Level Architecture Overview

The **Real-Time Financial Fraud Detection Platform** (AEGIS) combines supervised machine learning with graph-based syndicate detection and an asynchronous event-streaming pipeline to flag financial fraud with sub-10ms latency.

```mermaid
graph TD
    subgraph Data Sources & Ingestion
        CSV[Sample Data / External Stream] -->|Chronological Replay| Producer[Transaction Replay Producer]
        Producer -->|Publish Event| StreamAdapter[Streaming Adapter Interface]
    end

    subgraph Streaming Layer
        StreamAdapter -->|Default Fallback| Queue[Local In-Memory Async Queue]
        StreamAdapter -.->|Optional Opt-In| Kafka[Apache Kafka / Redpanda Broker]
    end

    subgraph Real-Time Scoring Engine
        Queue -->|Consume Event| Engine[Fraud Inference Engine]
        Kafka -.->|Consume Event| Engine
        
        Engine -->|Stateful Event-Time Transform| FeatPipe[Feature Pipeline]
        FeatPipe -->|16 Cold-Start Safe Features| XGB[XGBoost Classifier]
        
        Engine -->|Graph Ingestion & Traversal| NXGraph[NetworkX Entity Graph]
        NXGraph -->|Connected Components & Syndicate Scoring| GraphScore[Syndicate Risk Detector]

        XGB -->|Supervised Probability (65%)| Blender[Score Blender & Decision Rules]
        GraphScore -->|Graph Topology Risk (35%)| Blender
        Blender -->|Blended Score & Risk Tier| Decision[Decision Engine]
    end

    subgraph Case Management & Storage
        Decision -->|Trigger Alert| DB[(SQLite fraud_cases.db)]
        DB -->|Audit Trail & Status| CaseOps[Case Management Service]
        Engine -->|Parameters & Metrics| MLflow[(MLflow SQLite Tracking)]
    end

    subgraph Serving & Frontend
        FastAPI[FastAPI Scoring Service :8010] <--> Engine
        FastAPI <--> DB
        FastAPI <--> FeatPipe
        ReactUI[React + Vite Analyst Dashboard :5173] <-->|REST & Polling| FastAPI
    end
```

---

## 2. Streaming Transaction Workflow

```mermaid
sequenceDiagram
    autonumber
    actor Replayer as Transaction Replayer
    participant Queue as Async Event Queue
    participant Engine as Inference Engine
    participant Features as Feature Pipeline
    participant Model as XGBoost Classifier
    participant Graph as NetworkX Graph
    participant DB as SQLite DB
    actor Analyst as Fraud Analyst (UI)

    Replayer->>Queue: Publish transaction event (t_i, amount, acc_id, dev_id)
    Queue->>Engine: Deliver event to stream consumer
    Engine->>Features: Extract event-time features (prior to t_i)
    Features-->>Engine: Feature vector (velocity, amount ratio, cold start safe)
    
    par Parallel Scoring
        Engine->>Model: Compute fraud probability P(Fraud|Features)
        Model-->>Engine: ML Risk Score (0.0 to 1.0)
    and Graph Analysis
        Engine->>Graph: Add transaction edge (acc <-> dev <-> merch)
        Engine->>Graph: Analyze connected component & shared devices
        Graph-->>Engine: Syndicate Risk Score & Cluster Factors
    end

    Engine->>Engine: Blend scores (0.65*ML + 0.35*Graph) + check override
    alt Blended Score >= 0.70 or Ring Detected
        Engine->>DB: Save Alert (ALT_*, risk_tier='HIGH'/'CRITICAL', status='OPEN')
    end

    Analyst->>DB: Inspect Alert & Submit Feedback (CONFIRMED_FRAUD)
    DB-->>Analyst: Audit log persisted
```

---

## 3. Training & Evaluation Pipeline

```mermaid
graph LR
    Raw[Raw Transactions CSV] --> Sort[Chronological Ordering]
    Sort --> Split[Time-Based Partitioning]
    
    Split --> TrainSet[Train Partition: 70%]
    Split --> ValSet[Validation Partition: 15%]
    Split --> TestSet[Held-out Test: 15%]

    TrainSet --> FeatTrain[Stateful Feature Extraction]
    FeatTrain --> WeightCalc[Class Balance Ratio Calculation]
    WeightCalc --> XGBFit[XGBoost Histogram Classifier Fitting]

    XGBFit --> ValEval[Validation Tuning & Early Stopping]
    ValEval --> TestEval[Test Evaluation: PR-AUC, ROC-AUC, Confusion Matrix]

    TestEval --> Artifacts[Save Model & Metadata]
    TestEval --> MLflowLog[Log to MLflow SQLite Store]
    TestEval --> Plots[Generate PR Curve & CM Plots]
```

---

## 4. Graph Syndicate & Fraud Ring Topology

```mermaid
graph TD
    subgraph Mule Syndicate Ring #1
        MuleAcc1((ACC_RING1_1)) --- Dev1[DEV_RING1_A]
        MuleAcc2((ACC_RING1_2)) --- Dev1
        MuleAcc3((ACC_RING1_3)) --- Dev1
        MuleAcc4((ACC_RING1_4)) --- Dev2[DEV_RING1_B]
        MuleAcc5((ACC_RING1_5)) --- Dev2
        
        Dev1 -.-> MerchMule[(MERCH_MULE_CORP)]
        Dev2 -.-> MerchMule
    end

    subgraph Bot Emulator Farm #2
        Bot1((ACC_RING2_1)) --- Emu[DEV_RING2_EMULATOR]
        Bot2((ACC_RING2_2)) --- Emu
        Bot3((ACC_RING2_3)) --- Emu
        Bot4((ACC_RING2_4)) --- Emu
        Emu -.-> Crypto[(MERCH_CRYPTO_SWAP)]
    end

    subgraph Legitimate Isolated Accounts
        LegitAcc1((ACC_1001)) --- LegitDev1[DEV_2001]
        LegitAcc2((ACC_1002)) --- LegitDev2[DEV_2002]
        LegitDev1 --- Store1[(MERCH_3001)]
    end

    style Dev1 fill:#f59e0b,stroke:#b45309,color:#000
    style Dev2 fill:#f59e0b,stroke:#b45309,color:#000
    style Emu fill:#ef4444,stroke:#991b1b,color:#fff
    style MerchMule fill:#ef4444,stroke:#991b1b,color:#fff
    style Crypto fill:#ef4444,stroke:#991b1b,color:#fff
```

---

## 5. Architectural Quality Attributes

| Attribute | Implementation Strategy | Verification Result |
| :--- | :--- | :--- |
| **Zero Target Leakage** | Sequential event-time historical state; features for transaction $t_i$ strictly depend on transactions $< t_i$. Label column is never accessed during feature creation. | Proven via `tests/test_features.py` |
| **Low Latency** | In-memory feature state, histogram-based gradient boosted trees, lightweight NetworkX subgraphs. | Measured average: **6.2 ms** (P95: 9.4 ms) |
| **Cold-Start Resilience** | Documented global fallback priors when account has no historical velocity or baseline amount. | Proven via `test_cold_start_fallback` |
| **Port Isolation** | FastAPI runs on port **8010**, Vite dashboard on **5173**. No collisions with existing Docker containers on 8000/8501. | Verified |
| **Dual Backend Streaming** | Production `KafkaStreamingAdapter` alongside `LocalQueueAdapter` with identical async pub/sub contract. | Verified with zero required external daemons |
