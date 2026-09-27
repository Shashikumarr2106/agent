Yes. Below is the **final end-to-end Markdown architecture** for your project, combining everything we discussed: **FastAPI + LangGraph + MCP + PostgreSQL + pgvector + SQL + Analysis SDK + skill generation + human approval + chart generation + persistence + Docker + future Kubernetes**.

You can save this directly as your project architecture document.

# AI Data Analyst Agent — Complete Architecture

## 1. Project Goal

Build an AI-powered data analysis application where a user can:

1. Upload a CSV dataset.
2. Ask questions about the dataset.
3. Get an automatically generated analysis plan.
4. Reuse existing analysis skills from a vector database.
5. Generate a new analysis skill when no existing skill is available.
6. Approve generated analysis logic before execution.
7. Execute calculations through an Analysis SDK rather than asking the LLM to perform numerical calculations.
8. Generate charts from the analysis results.
9. Receive Markdown + interactive chart output in the frontend.
10. Give feedback and correct an analysis.
11. Version and improve analysis skills over time.
12. Maintain session/job history and execution logs.
13. Eventually scale the application using Docker and Kubernetes.

---

# 2. High-Level Architecture

```text
                                  USER
                                   │
                                   ▼
                         ┌───────────────────┐
                         │     FRONTEND      │
                         │                   │
                         │ CSV Upload        │
                         │ Chat              │
                         │ Approval          │
                         │ Feedback          │
                         │ Charts            │
                         └─────────┬─────────┘
                                   │
                             HTTP / WebSocket
                                   │
                                   ▼
                         ┌───────────────────┐
                         │      FASTAPI      │
                         │                   │
                         │ Application API   │
                         │ Authentication    │
                         │ Uploads           │
                         │ Sessions          │
                         │ Jobs              │
                         │ Streaming         │
                         └─────────┬─────────┘
                                   │
                                   ▼
                         ┌───────────────────┐
                         │     LANGGRAPH     │
                         │                   │
                         │ Agent Orchestrator│
                         │ State Management  │
                         │ Routing           │
                         │ Planning          │
                         └─────────┬─────────┘
                                   │
                                   ▼
                         ┌───────────────────┐
                         │     MCP CLIENT    │
                         └─────────┬─────────┘
                                   │
                                   ▼
                    ┌─────────────────────────────┐
                    │          MCP SERVER         │
                    │                             │
                    │ Data Tools                   │
                    │ Skill Tools                  │
                    │ Analysis Tools               │
                    │ Chart Tools                  │
                    └──────┬────────┬────────┬────┘
                           │        │        │
                           ▼        ▼        ▼
                      PostgreSQL  pgvector  Analysis SDK
```

---

# 3. Responsibility of Each Technology

| Technology       | Responsibility                           |
| ---------------- | ---------------------------------------- |
| React / Frontend | User interface                           |
| FastAPI          | Application/API layer                    |
| LangGraph        | Agent orchestration and state            |
| LangChain        | LLM/tool integrations                    |
| MCP              | Standardized agent-to-tool communication |
| PostgreSQL       | Application + dataset persistence        |
| pgvector         | Skill vector search                      |
| SQL              | Retrieve required dataset information    |
| Analysis SDK     | Actual calculations                      |
| Chart Generator  | Generate chart specifications            |
| Docker           | Containerization                         |
| Kubernetes       | Future scaling                           |
| LLM              | Reasoning, planning, generation          |

---

# 4. Why FastAPI AND MCP?

They are not replacements.

## FastAPI

FastAPI is the application's front door.

Examples:

```text
POST /datasets/upload
POST /chat
POST /analysis/approve
POST /analysis/feedback
GET  /jobs/{job_id}
GET  /sessions/{session_id}
```

The frontend communicates with FastAPI.

## MCP

MCP exposes tools to the AI agent.

Examples:

```text
get_dataset_schema()
execute_sql()
search_skills()
get_skill()
save_skill()
update_skill()
run_analysis()
validate_formula()
generate_chart()
```

Therefore:

```text
Frontend
   ↓
FastAPI
   ↓
LangGraph
   ↓
MCP
   ↓
Tools
```

---

# 5. Main Components

## 5.1 Frontend

The frontend provides:

* CSV upload
* Chat interface
* Analysis plan display
* Generated method display
* Approval/rejection
* Results
* Charts
* Markdown
* Job status
* Error messages
* Feedback

Example:

```text
┌──────────────────────────────────────────┐
│ Dataset: sales.csv                       │
│                                          │
│ Ask a question:                          │
│                                          │
│ "Find correlation between sales/profit"  │
│                                          │
│              [ Analyze ]                 │
└──────────────────────────────────────────┘
```

---

# 6. FastAPI Layer

FastAPI handles application-level communication.

Example endpoints:

```text
POST /datasets/upload

POST /chat

POST /analysis/approve

POST /analysis/reject

POST /analysis/feedback

GET /jobs/{job_id}

GET /sessions/{session_id}
```

FastAPI should NOT contain the complete analysis workflow.

Instead:

```text
FastAPI
   ↓
LangGraph
   ↓
MCP
   ↓
Tools
```

---

# 7. LangGraph

LangGraph is the main workflow/orchestration layer.

It controls:

* Planning
* Routing
* Skill search
* SQL generation
* Human approval
* Analysis execution
* Validation
* Chart generation
* Error handling
* Feedback
* State
* Checkpointing

---

# 8. LangGraph Workflow

```text
START
  │
  ▼
Load Session
  │
  ▼
Load Dataset
  │
  ▼
Inspect Schema
  │
  ▼
Understand User Question
  │
  ▼
Check Question Relevance
  │
  ├──────── NOT RELEVANT ────────┐
  │                              │
  │                              ▼
  │                    Suggest Data Analyses
  │                              │
  └───────────────┬──────────────┘
                  │
                  ▼
          Create Analysis Plan
                  │
                  ▼
           Search Skill Index
                  │
          ┌───────┴────────┐
          │                │
       FOUND            NOT FOUND
          │                │
          ▼                ▼
    Retrieve Skill    Generate Method
          │                │
          │                ▼
          │          Validate Method
          │                │
          │                ▼
          │          Human Approval
          │                │
          │        ┌───────┴────────┐
          │        │                │
          │     APPROVED         REJECTED
          │        │                │
          │        │          Modify Method
          │        │                │
          │        └───────┬────────┘
          │                │
          └────────┬───────┘
                   ▼
             Generate SQL
                   │
                   ▼
              Execute SQL
                   │
                   ▼
             Analysis SDK
                   │
                   ▼
             Validate Result
                   │
                   ▼
           Generate Chart Spec
                   │
                   ▼
             Save Results
                   │
                   ▼
           Return Final Response
                   │
                   ▼
                  END
```

---

# 9. LangGraph State

The graph maintains a shared state.

```python
class AnalysisState:

    session_id: str
    job_id: str

    dataset_id: str

    question: str

    dataset_schema: dict

    analysis_plan: dict

    skill_found: bool

    skill_id: str | None

    skill_version: int | None

    analysis_method: dict

    generated_code: str | None

    sql_query: str | None

    retrieved_data: dict | None

    sdk_output: dict | None

    validation_result: dict | None

    chart_spec: dict | None

    user_approved: bool

    user_feedback: str | None

    status: str

    error: str | None
```

This allows the graph to pause and resume.

---

# 10. CSV Upload Flow

User uploads:

```text
sales.csv
```

Flow:

```text
CSV
 ↓
FastAPI
 ↓
Ingestion Service
 ↓
Schema Detection
 ↓
PostgreSQL
 ↓
Dataset Metadata
```

Example:

```text
dataset_id = D1001
```

Metadata:

```text
filename: sales.csv
row_count: 10,000,000
columns:
    date
    product
    region
    sales
    profit
    quantity
```

---

# 11. Actual Dataset Storage

The actual CSV data should NOT be stored in the skill vector database.

Instead:

```text
ACTUAL DATA
    ↓
PostgreSQL
```

Example:

```text
sales_data

id
date
product
region
sales
profit
quantity
```

The skill vector database contains:

```text
ANALYSIS KNOWLEDGE

correlation
regression
mean
median
standard deviation
coefficient of variation
sales trend
customer segmentation
etc.
```

---

# 12. Large Dataset Strategy

Never send the entire dataset to the LLM.

Bad approach:

```text
10 million rows
      ↓
LLM
```

Correct approach:

```text
10 million rows
      ↓
SQL
      ↓
Filter / Aggregate
      ↓
Relevant subset
      ↓
Analysis SDK
```

Example:

User asks:

```text
"Give average revenue by state."
```

SQL:

```sql
SELECT
    state,
    AVG(revenue) AS avg_revenue
FROM sales
GROUP BY state;
```

The LLM does not need the 10 million original rows.

---

# 13. Question Relevance

The system first checks:

```text
Is the question relevant to this dataset?
```

Example:

Dataset:

```text
sales
profit
region
product
```

Question:

```text
"Which region has the highest sales?"
```

Result:

```text
RELEVANT
```

But:

```text
"What is the weather tomorrow?"
```

Result:

```text
NOT RELEVANT
```

For an irrelevant question, the system can explain that the question cannot be answered from the uploaded dataset and instead offer useful analyses based on the available data.

---

# 14. User Provides No Question

If the user uploads a CSV and doesn't ask anything:

```text
Upload CSV
   ↓
Inspect schema
   ↓
Understand data
   ↓
Find applicable analysis skills
   ↓
Select useful analyses
   ↓
Execute
```

Example sales dataset:

```text
1. Monthly sales trend
2. Sales by region
3. Profit by product
4. Sales/profit correlation
5. Quantity vs sales relationship
```

The five analyses should be selected based on the actual dataset rather than being permanently hardcoded.

---

# 15. MCP Architecture

Initially, use one MCP server.

```text
                 LANGGRAPH
                     │
                     ▼
                 MCP CLIENT
                     │
                     ▼
              ┌──────────────┐
              │ MCP SERVER   │
              └──────┬───────┘
                     │
       ┌─────────────┼──────────────┐
       │             │              │
       ▼             ▼              ▼
   Data Tools    Skill Tools    Analysis Tools
```

Later you can split them.

```text
MCP Client
    │
    ├── Data MCP
    │
    ├── Skill MCP
    │
    ├── Analysis MCP
    │
    └── Chart MCP
```

For your first version, one MCP server is simpler.

---

# 16. Data MCP Tools

Example tools:

```text
get_dataset_schema()

get_dataset_metadata()

get_sample_data()

execute_sql()

get_dataset_statistics()
```

Example:

```text
execute_sql(
    dataset_id="D1001",
    sql="SELECT region, AVG(sales) FROM sales GROUP BY region"
)
```

---

# 17. Skill MCP Tools

Skill tools:

```text
search_skills()

get_skill()

get_skill_version()

save_skill()

update_skill()

list_skill_versions()
```

Example:

```text
search_skills(
    "correlation between two numerical variables"
)
```

Result:

```text
skill_id:
correlation_001

version:
3

similarity:
0.94
```

---

# 18. Skill Vector Database

Use:

```text
PostgreSQL
     +
pgvector
```

This means you don't necessarily need a separate vector database initially.

Skill record:

```text
skill_id
name
description
required_inputs
formula
logic
code
examples
validation_rules
version
status
embedding
created_at
updated_at
```

---

# 19. Skill Retrieval

Example:

User:

```text
"Find correlation between sales and profit."
```

Skill search:

```text
Question
   ↓
Embedding
   ↓
pgvector
   ↓
Similarity search
```

Result:

```text
correlation_001
```

Then retrieve:

```text
formula
logic
code
required columns
validation rules
```

---

# 20. Existing Skill Flow

If the skill exists:

```text
Question
   ↓
Search Skill
   ↓
Skill Found
   ↓
Retrieve Skill
   ↓
Generate SQL
   ↓
Execute SQL
   ↓
Pass data + skill logic to Analysis SDK
   ↓
SDK calculates
   ↓
Validate result
   ↓
Generate chart
   ↓
Return result
```

---

# 21. Analysis SDK

The SDK performs the actual mathematical/data calculation.

The LLM should not be responsible for numerical calculations.

Example:

```text
LLM
 ↓
"Use Pearson correlation"
 ↓
Skill
 ↓
Analysis SDK
 ↓
0.82
```

For example:

```python
result = analysis_sdk.run(
    method="pearson_correlation",
    data=data
)
```

Output:

```json
{
    "metric": "pearson_correlation",
    "value": 0.82,
    "sample_size": 98234
}
```

---

# 22. Why Use an SDK?

It provides deterministic execution.

Instead of:

```text
LLM calculates:
0.82
```

you have:

```text
LLM decides:
"Run Pearson correlation"

SDK calculates:
0.82
```

This is better for reproducibility and validation.

---

# 23. Skill NOT Found

If no skill exists:

```text
Question
   ↓
Search Skills
   ↓
NOT FOUND
   ↓
Generate Analysis Method
   ↓
Validate Method
   ↓
Show User
   ↓
User Approval
   ↓
Execute
```

Example:

```text
Coefficient of Variation

Formula:

CV = standard deviation / mean × 100

Required:
revenue

Steps:
1. Remove invalid values
2. Calculate mean
3. Calculate standard deviation
4. Calculate CV
```

---

# 24. Human Approval

The UI displays:

```text
┌─────────────────────────────────────┐
│ Proposed Analysis                   │
│                                     │
│ Coefficient of Variation            │
│                                     │
│ Formula:                            │
│ CV = std / mean × 100               │
│                                     │
│ Required column: revenue            │
│                                     │
│ Generated method:                   │
│ ...                                 │
│                                     │
│ [ APPROVE ]       [ MODIFY ]        │
└─────────────────────────────────────┘
```

Only after approval:

```text
Generated Method
       ↓
Analysis SDK
```

---

# 25. Saving a New Skill

After successful execution:

```text
Generated Skill
      ↓
Validation
      ↓
User Approved
      ↓
Execution Successful
      ↓
Save Skill
      ↓
Generate Embedding
      ↓
pgvector
```

Example:

```text
skill_id:
coefficient_variation_001

version:
1

formula:
std / mean * 100

code:
...

created_from_job:
J5001
```

Next time, the skill can be retrieved.

---

# 26. Skill Versioning

Never blindly overwrite a skill.

Example:

```text
correlation_001
│
├── v1
├── v2
└── v3
```

If the user changes the methodology:

```text
Existing Skill v1
       ↓
User correction
       ↓
Validate correction
       ↓
Create v2
       ↓
Execute
       ↓
Store v2
```

This provides an audit trail.

---

# 27. User Says "The Result Is Wrong"

Flow:

```text
User Feedback
      ↓
Understand Correction
      ↓
Validate Requested Formula/Logic
      ↓
      ├── Valid
      │     ↓
      │   Create New Version
      │     ↓
      │   Re-run
      │
      └── Invalid
            ↓
       Explain why
            ↓
       Suggest correction
```

Example:

```text
User:
"Use population standard deviation instead."
```

System:

```text
Validate request
       ↓
Create skill version 2
       ↓
Execute SDK
       ↓
Return new result
```

---

# 28. Chart Generation

After the analysis SDK returns the result:

```text
Dataset / Aggregated Data
          +
Analysis Output
          +
Question
          ↓
Chart Generator
          ↓
Chart Specification
```

Example:

```json
{
    "type": "bar",
    "title": "Sales by Region",
    "x": "region",
    "y": "sales",
    "data": [
        {
            "region": "North",
            "sales": 120000
        },
        {
            "region": "South",
            "sales": 90000
        }
    ]
}
```

---

# 29. Chart Types

The system can support:

```text
Bar
Line
Pie
Scatter
Funnel
Area
Histogram
Box Plot
Heatmap
```

Chart selection depends on the result/data shape.

---

# 30. Frontend Rendering

Backend returns:

```text
Markdown
+
Chart Specification
```

Example:

```markdown
## Sales by Region

The analysis shows the sales distribution across regions.

{{chart:chart_001}}
```

The frontend converts:

```text
{{chart:chart_001}}
```

into an interactive chart.

This is better than generating raw HTML from the LLM.

---

# 31. Final Response Structure

Your backend can return:

```json
{
    "job_id": "J1001",

    "status": "completed",

    "markdown": "## Sales by Region\n...",

    "analysis": {
        "method": "average_sales_by_region",
        "result": []
    },

    "chart": {
        "type": "bar",
        "title": "Sales by Region",
        "data": []
    }
}
```

The frontend renders the result.

---

# 32. Database Architecture

Use PostgreSQL initially.

```text
                    PostgreSQL
                         │
        ┌────────────────┼─────────────────┐
        │                │                 │
        ▼                ▼                 ▼
   Application       Dataset Data       pgvector
      Data                               Skills
```

Tables:

```text
users

sessions

datasets

analysis_jobs

analysis_results

skills

skill_versions

execution_logs
```

---

# 33. Important Tables

## users

```text
user_id
email
created_at
```

## sessions

```text
session_id
user_id
created_at
updated_at
```

## datasets

```text
dataset_id
user_id
filename
schema
row_count
created_at
```

## analysis_jobs

```text
job_id
session_id
dataset_id
question
status
created_at
completed_at
```

## skills

```text
skill_id
name
description
current_version
created_at
updated_at
```

## skill_versions

```text
skill_id
version
formula
logic
code
examples
validation_rules
created_at
```

## execution_logs

```text
log_id
job_id
step
status
input
output
error
timestamp
```

---

# 34. Session and Job IDs

Use separate IDs.

```text
session_id
```

represents the conversation.

```text
job_id
```

represents one analysis task.

Example:

```text
Session:
S100

Jobs:
J1001
J1002
J1003
```

A job can contain:

```text
dataset_id
question
skill_id
skill_version
SQL
SDK output
chart
status
logs
```

---

# 35. Complete Example

User uploads:

```text
sales.csv
```

Dataset:

```text
date
region
product
sales
profit
quantity
```

User asks:

```text
"Which region has the highest average profit?"
```

Flow:

```text
USER
 ↓
FRONTEND
 ↓
FASTAPI
 ↓
LANGGRAPH
 ↓
Get Schema
 ↓
Question Relevant?
 ↓
YES
 ↓
Search Skill
 ↓
Skill Found
 ↓
Retrieve Skill
 ↓
Generate SQL
 ↓
MCP execute_sql()
 ↓
PostgreSQL
 ↓
Aggregated Data
 ↓
Analysis SDK
 ↓
Calculate result
 ↓
Validation
 ↓
Chart Generator
 ↓
Chart Specification
 ↓
Save Job
 ↓
Frontend
```

SQL:

```sql
SELECT
    region,
    AVG(profit) AS avg_profit
FROM sales
GROUP BY region;
```

SDK:

```text
North → 5200
South → 4300
East  → 3900
West  → 4800
```

Chart:

```text
Bar Chart
```

Final UI:

```text
## Average Profit by Region

North has the highest average profit.

[Interactive Bar Chart]

| Region | Average Profit |
|---|---:|
| North | 5200 |
| West  | 4800 |
| South | 4300 |
| East  | 3900 |
```

---

# 36. No-Skill Example

User:

```text
"Calculate coefficient of variation for revenue."
```

Flow:

```text
Question
 ↓
Skill Search
 ↓
No skill
 ↓
Generate Method
 ↓
Validate Method
 ↓
Show User
 ↓
User Approves
 ↓
Generate SQL
 ↓
Execute SQL
 ↓
Analysis SDK
 ↓
Validate Result
 ↓
Save Skill v1
 ↓
Generate Chart
 ↓
Return Result
```

Next user:

```text
"Calculate CV for profit."
```

Now:

```text
Skill Search
 ↓
Coefficient of Variation Skill
 ↓
Retrieve existing skill
 ↓
Reuse
```

No need to regenerate the method.

---

# 37. Security for SQL

Do not allow unrestricted SQL execution.

The SQL tool should enforce:

```text
SELECT only
```

and preferably:

```text
Dataset-specific tables
Parameterized queries
Row limits
Result-size limits
Query timeout
No DROP
No DELETE
No UPDATE
No INSERT
No arbitrary system commands
```

Example:

```text
Allowed:

SELECT region, AVG(sales)
FROM dataset_1001
GROUP BY region;
```

Not allowed:

```text
DROP TABLE dataset_1001;
```

---

# 38. Security for Generated Code

Generated analysis code is potentially executable code.

Do NOT run arbitrary generated code directly inside your main FastAPI process in production.

Safer architecture:

```text
LangGraph
    ↓
Analysis MCP
    ↓
Sandbox / Worker
    ↓
Analysis SDK
    ↓
Result
```

Initially, you can keep the SDK controlled and predefined.

Later:

```text
Docker sandbox
```

or isolated worker environments can execute generated code.

---

# 39. Logging

Every job should record:

```text
session_id
job_id
dataset_id

question

schema inspection

skill search

skill ID

skill version

generated SQL

SQL execution

analysis execution

analysis output

chart generation

user approval

user feedback

errors

timestamps
```

Example:

```text
J5001

10:00:01 question_received
10:00:02 schema_loaded
10:00:03 skill_search
10:00:03 skill_found
10:00:04 sql_generated
10:00:04 sql_executed
10:00:05 sdk_started
10:00:05 sdk_completed
10:00:06 chart_generated
10:00:06 completed
```

---

# 40. Recommended Project Structure

```text
data-analysis-agent/
│
├── backend/
│   │
│   ├── api/
│   │   ├── routes_upload.py
│   │   ├── routes_chat.py
│   │   ├── routes_analysis.py
│   │   └── routes_feedback.py
│   │
│   ├── graph/
│   │   ├── state.py
│   │   ├── graph.py
│   │   ├── planner.py
│   │   ├── skill_node.py
│   │   ├── sql_node.py
│   │   ├── approval_node.py
│   │   ├── analysis_node.py
│   │   ├── validation_node.py
│   │   └── chart_node.py
│   │
│   ├── mcp/
│   │   ├── server.py
│   │   ├── data_tools.py
│   │   ├── skill_tools.py
│   │   ├── analysis_tools.py
│   │   └── chart_tools.py
│   │
│   ├── services/
│   │   ├── ingestion.py
│   │   ├── database.py
│   │   ├── embedding.py
│   │   ├── skill_service.py
│   │   ├── analysis_service.py
│   │   └── chart_service.py
│   │
│   ├── models/
│   │   ├── dataset.py
│   │   ├── skill.py
│   │   ├── job.py
│   │   └── result.py
│   │
│   └── main.py
│
├── frontend/
│   ├── components/
│   │   ├── Chat.jsx
│   │   ├── Upload.jsx
│   │   ├── AnalysisPlan.jsx
│   │   ├── Approval.jsx
│   │   ├── Result.jsx
│   │   └── Chart.jsx
│   │
│   └── ...
│
├── skills/
│   ├── correlation/
│   ├── regression/
│   ├── mean/
│   ├── median/
│   └── ...
│
├── tests/
│
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── README.md
```

---

# 41. Initial Technology Stack

```text
Frontend
    React

Backend
    Python
    FastAPI

Agent
    LangChain
    LangGraph

Tool Protocol
    MCP

Database
    PostgreSQL

Vector Search
    pgvector

Data Analysis
    Python
    Pandas
    NumPy
    SciPy
    Analysis SDK

LLM
    LLM API / local model

Containerization
    Docker

Initial Deployment
    Docker + managed PostgreSQL

Future Scaling
    Kubernetes
```

---

# 42. Docker — Initial Stage

Do not start with Kubernetes.

Initial:

```text
Docker
 │
 └── Application
       ├── FastAPI
       ├── LangGraph
       └── MCP
```

Database:

```text
PostgreSQL
+
pgvector
```

You can also use Docker Compose locally:

```text
docker-compose
 │
 ├── backend
 ├── postgres
 └── frontend
```

---

# 43. Future Kubernetes Architecture

Only when the application needs scaling:

```text
                         LOAD BALANCER
                               │
                               ▼
                         KUBERNETES
                               │
             ┌─────────────────┼─────────────────┐
             ▼                 ▼                 ▼
         FastAPI × N       Workers × N       MCP × N
             │                 │                 │
             └─────────────────┼─────────────────┘
                               │
                               ▼
                         PostgreSQL
                          + pgvector
```

Later you can add:

```text
Redis
Message Queue
Background Workers
Object Storage
Monitoring
Autoscaling
```

---

# 44. What You Build First

Do NOT build the entire architecture at once.

## Phase 1 — Basic Data Analysis

```text
CSV
 ↓
PostgreSQL
 ↓
Question
 ↓
SQL
 ↓
Analysis SDK
 ↓
Result
```

---

## Phase 2 — LangGraph

Add:

```text
Question
 ↓
LangGraph
 ↓
Plan
 ↓
SQL
 ↓
SDK
```

---

## Phase 3 — MCP

Add:

```text
LangGraph
 ↓
MCP
 ↓
Data Tools
 ↓
Skill Tools
 ↓
Analysis Tools
```

---

## Phase 4 — Skill Vector Database

Add:

```text
Question
 ↓
pgvector
 ↓
Search Skill
 ↓
Existing Skill
 ↓
Execute
```

---

## Phase 5 — Skill Generation

Add:

```text
No Skill
 ↓
Generate Method
 ↓
User Approval
 ↓
Execute
 ↓
Save Skill
```

---

## Phase 6 — Feedback + Versioning

Add:

```text
Wrong Result
 ↓
User Feedback
 ↓
Validate Correction
 ↓
New Skill Version
 ↓
Re-run
```

---

## Phase 7 — Charts

Add:

```text
Analysis Result
 ↓
Chart Generator
 ↓
Chart JSON
 ↓
Frontend Widget
```

---

## Phase 8 — Persistence + Logging

Add:

```text
Session
Job
Skill Version
Execution Logs
Results
```

---

## Phase 9 — Docker

Containerize:

```text
FastAPI
LangGraph
MCP
Frontend
PostgreSQL
```

---

## Phase 10 — Kubernetes

Only after the application works correctly:

```text
Docker
 ↓
Kubernetes
 ↓
Multiple replicas
 ↓
Load balancing
 ↓
Autoscaling
 ↓
Workers
```

---

# 45. Final Architecture

The final mental model for the whole project is:

```text
                         ┌──────────────┐
                         │     USER     │
                         └──────┬───────┘
                                │
                                ▼
                         ┌──────────────┐
                         │   FRONTEND   │
                         └──────┬───────┘
                                │
                                ▼
                         ┌──────────────┐
                         │   FASTAPI    │
                         └──────┬───────┘
                                │
                                ▼
                         ┌──────────────┐
                         │  LANGGRAPH   │
                         │              │
                         │  PLAN        │
                         │  ROUTE       │
                         │  STATE       │
                         │  APPROVAL    │
                         └──────┬───────┘
                                │
                                ▼
                         ┌──────────────┐
                         │  MCP CLIENT  │
                         └──────┬───────┘
                                │
                 ┌──────────────┼──────────────┐
                 │              │              │
                 ▼              ▼              ▼
          ┌────────────┐ ┌────────────┐ ┌────────────┐
          │ DATA TOOLS │ │SKILL TOOLS │ │ ANALYSIS   │
          │            │ │            │ │ TOOLS      │
          └─────┬──────┘ └─────┬──────┘ └─────┬──────┘
                │              │              │
                ▼              ▼              ▼
          ┌──────────┐   ┌──────────┐   ┌────────────┐
          │PostgreSQL│   │ pgvector │   │ Analysis   │
          │          │   │          │   │ SDK        │
          │CSV Data  │   │ Skills   │   │            │
          └──────────┘   └──────────┘   └─────┬──────┘
                                               │
                                               ▼
                                      ┌────────────────┐
                                      │ VALIDATION     │
                                      └───────┬────────┘
                                              │
                                              ▼
                                      ┌────────────────┐
                                      │ CHART GENERATOR│
                                      └───────┬────────┘
                                              │
                                              ▼
                                      ┌────────────────┐
                                      │ CHART SPEC     │
                                      │ + MARKDOWN     │
                                      └───────┬────────┘
                                              │
                                              ▼
                                      ┌────────────────┐
                                      │    FRONTEND    │
                                      │                │
                                      │ Table          │
                                      │ Markdown       │
                                      │ Charts         │
                                      └────────────────┘
```

# 46. One-Line Explanation for Interviews

> **"I built an AI data-analysis agent where FastAPI exposes the application APIs, LangGraph orchestrates the stateful analysis workflow, MCP provides standardized access to data, skill, analysis and chart tools, PostgreSQL stores the datasets and application state, pgvector stores reusable analysis skills, SQL retrieves only the required data, and a separate Analysis SDK performs the actual calculations. When a skill doesn't exist, the agent generates and validates the analysis logic, asks for human approval, executes it, and stores the approved logic as a versioned reusable skill."**

# 47. Most Important Design Principle

Remember this:

```text
             WHO DECIDES?
                 │
              LangGraph
                 │
                 ▼
             MCP TOOLS
                 │
        ┌────────┼─────────┐
        ▼        ▼         ▼
       DATA    SKILLS    ANALYSIS
        │        │         │
        ▼        ▼         ▼
       SQL    pgvector     SDK
```

Or even simpler:

```text
LLM / LangGraph
      =
"What should I do?"

MCP
      =
"How do I access the capability?"

Skill
      =
"How should this analysis be performed?"

SQL
      =
"What data do I need?"

Analysis SDK
      =
"Actually calculate it."

Chart Generator
      =
"How should I visualize it?"

Frontend
      =
"How should I show it to the user?"
```

That separation is the core architecture of your project.

USER REQUEST
     │
     ▼
UNDERSTAND REQUEST
     │
     ▼
CREATE ANALYSIS PLAN
     │
     ▼
SHOW PLAN TO USER
     │
     ├───────────────┐
     │               │
 APPROVE          MODIFY
     │               │
     │               ▼
     │        UPDATE REQUEST
     │               │
     │               ▼
     │        RE-CREATE PLAN
     │               │
     │          ┌────┴────┐
     │          │         │
     │       APPROVE    MODIFY
     │          │
     └──────────┘
             │
             ▼
       SEARCH SKILL
             │
             ▼
        GENERATE SQL
             │
             ▼
        EXECUTE SQL
             │
             ▼
        ANALYSIS SDK
             │
             ▼
        VALIDATE RESULT
             │
             ▼
       GENERATE CHART
             │
             ▼
        SHOW RESULT
             │
             ▼
       USER FEEDBACK
             │
       ┌─────┴─────┐
       │           │
   ACCEPT       MODIFY
       │           │
      END          ▼
             UPDATE REQUEST
                  │
                  ▼
              RE-PLAN
