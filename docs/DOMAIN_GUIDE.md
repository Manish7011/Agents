# Domain Guide: Implementation Patterns & Use Cases

This guide explains the 9 domains in the ecosystem, their specialties, implementation patterns, and when to use each domain.

---

## Table of Contents

1. [Domain Overview](#domain-overview)
2. [Finance Domain](#finance-domain)
3. [Cybersecurity Domain](#cybersecurity-domain)
4. [E-Commerce Domain](#ecommerce-domain)
5. [Data Analytics Domain](#data-analytics-domain)
6. [DevOps Domain](#devops-domain)
7. [Healthcare Domain](#healthcare-domain)
8. [Human Resources Domain](#human-resources-domain)
9. [Business Intelligence Domain](#business-intelligence-domain)
10. [Education Domain](#education-domain)
11. [Cross-Domain Patterns](#cross-domain-patterns)
12. [Choosing a Domain](#choosing-a-domain)

---

## Domain Overview

```
ECOSYSTEM
├── 1. Finance
│   Purpose: Financial operations, reporting, risk management
│   Complexity: Medium
├── 2. Cybersecurity
│   Purpose: Vulnerability management, security ops
│   Complexity: Advanced
├── 3. E-Commerce
│   Purpose: Customer operations, commerce workflows
│   Complexity: Medium
├── 4. Data Analytics
│   Purpose: Data querying, business intelligence
│   Complexity: Medium
├── 5. DevOps
│   Purpose: Development ops, infrastructure automation
│   Complexity: Advanced
├── 6. Healthcare
│   Purpose: Clinical ops, hospital management
│   Complexity: Advanced
├── 7. Human Resources
│   Purpose: Talent management, HR operations
│   Complexity: Medium
├── 8. Business Intelligence
│   Purpose: Analytics, reporting, insights
│   Complexity: Easy
└── 9. Education
    Purpose: Academic ops, student management
    Complexity: Advanced
```

---

## Finance Domain

### Domain Focus

**Purpose**: Automate financial operations including reporting, analysis, loan processing, and risk management.

**Key Workflows**:
- Financial statement generation (GL, P&L, Balance Sheet)
- Cash flow analysis and forecasting
- Budget vs. actual variance analysis
- Loan application processing
- Credit risk assessment
- Automated board packs and executive summaries

### Specialists Pattern

Finance agents typically use these specialist types:

```
┌──────────────────────┐
│  Finance Supervisor  │
├──────────────────────┤
│
├─→ GL Specialist
│   ├─ Journal entry posting
│   ├─ Trial balance
│   └─ Account reconciliation
│
├─→ P&L Specialist
│   ├─ Revenue recognition
│   ├─ Expense allocation
│   └─ Profitability analysis
│
├─→ Risk Assessment Specialist
│   ├─ Credit risk scoring
│   ├─ Default probability
│   └─ Loss estimation
│
└─→ Reporting Specialist
    ├─ Report generation
    ├─ Email distribution
    └─ Archive management
```

### Data Schema Patterns

```python
# Core finance tables
class JournalEntry(Base):
    id: int
    account_id: int
    debit_amount: Decimal
    credit_amount: Decimal
    entry_date: DateTime
    description: str

class Account(Base):
    id: int
    code: str  # e.g., "1000"
    name: str
    type: str  # Asset, Liability, Equity, Revenue, Expense

class FinancialReport(Base):
    id: int
    report_type: str  # GL, PL, BalanceSheet
    period: str  # YYYY-MM
    generated_at: DateTime
    data: JSON
```

### Implementation Tips

1. **Precision**: Use Decimal, not float, for monetary values
2. **Audit Trail**: Log all journal entries with timestamps and user
3. **Period Management**: Use fiscal periods, not calendar months
4. **Reconciliation**: Build in balance checking (debits = credits)
5. **Access Control**: Implement role-based permissions (Accountant, Manager, CFO)

### Use Cases for Finance Domain

| Use Case | Specialists Needed | Complexity |
|----------|-------------------|-----------|
| Monthly financial reporting | GL, P&L, Reporting | Medium |
| Loan application processing | Risk Assessment, Validation | Medium |
| Cash flow forecasting | P&L, Reporting | Medium |
| Budget variance analysis | Budget, Actual, Reporting | Medium |

---

## Cybersecurity Domain

### Domain Focus

**Purpose**: Automate vulnerability scanning, dependency analysis, threat detection, and security operations.

**Key Workflows**:
- CVE (Common Vulnerabilities and Exposures) scanning
- Dependency vulnerability detection
- Network reconnaissance
- Security advisory analysis
- Threat reporting
- Autonomous security assessments

### Specialists Pattern

Cybersecurity agents typically use:

```
┌──────────────────────────┐
│ Cybersecurity Supervisor │
├──────────────────────────┤
│
├─→ CVE Specialist
│   ├─ CVE database lookup
│   ├─ Severity assessment
│   ├─ CVSS scoring
│   └─ Threat analysis
│
├─→ Dependency Specialist
│   ├─ Scan dependencies
│   ├─ Identify vulnerabilities
│   ├─ License compliance
│   └─ Update recommendations
│
├─→ Recon Specialist
│   ├─ DNS enumeration
│   ├─ Port scanning
│   ├─ WHOIS lookup
│   └─ Service detection
│
└─→ Reporting Specialist
    ├─ Vulnerability report
    ├─ Risk prioritization
    └─ Remediation guidance
```

### Data Schema Patterns

```python
class Vulnerability(Base):
    id: int
    cve_id: str  # e.g., CVE-2024-1234
    title: str
    description: str
    severity: str  # Critical, High, Medium, Low
    cvss_score: float
    affected_package: str
    fixed_version: str

class ScanResult(Base):
    id: int
    scan_type: str  # CVE, Dependency, Recon
    target: str  # URL, repo, IP
    found_vulnerabilities: int
    scan_date: DateTime
    report: JSON
```

### Implementation Tips

1. **External APIs**: Integrate with NVD, OSV, GitHub Advisory databases
2. **Async Processing**: Scans can be long-running (queue scans)
3. **Caching**: Cache CVE data to reduce API calls
4. **Filtering**: Allow false-positive filtering and exemptions
5. **Reporting**: Executive summaries vs. detailed technical reports

### Use Cases for Cybersecurity Domain

| Use Case | Specialists Needed | Complexity |
|----------|-------------------|-----------|
| Dependency scanning | CVE, Dependency | Advanced |
| Network recon | Recon, Reporting | Advanced |
| Vulnerability aggregation | CVE, Reporting | Advanced |
| Security assessment | All specialists | Advanced |

---

## E-Commerce Domain

### Domain Focus

**Purpose**: Automate customer support, order management, fraud detection, and commerce workflows.

**Key Workflows**:
- Customer inquiry routing
- Order management and fulfillment
- Return eligibility checking
- Fraud detection
- Payment processing
- Loyalty rewards management
- Email notifications

### Specialists Pattern

E-Commerce agents typically use:

```
┌──────────────────────┐
│ E-Commerce Supervisor│
├──────────────────────┤
│
├─→ Orders Specialist
│   ├─ Order creation
│   ├─ Status tracking
│   ├─ Fulfillment updates
│   └─ Shipping info
│
├─→ Returns Specialist
│   ├─ Return eligibility
│   ├─ RMA creation
│   ├─ Refund processing
│   └─ Fraud check
│
├─→ Payments Specialist
│   ├─ Payment processing
│   ├─ Invoice generation
│   ├─ Duplicate detection
│   └─ Reconciliation
│
└─→ Loyalty Specialist
    ├─ Points calculation
    ├─ Redemption
    └─ Status management
```

### Data Schema Patterns

```python
class Order(Base):
    id: int
    order_number: str
    customer_id: int
    order_date: DateTime
    total_amount: Decimal
    status: str  # Pending, Confirmed, Shipped, Delivered
    items: List[OrderItem]

class OrderItem(Base):
    id: int
    order_id: int
    product_id: int
    quantity: int
    unit_price: Decimal

class Return(Base):
    id: int
    order_id: int
    rma_number: str
    reason: str
    status: str  # Submitted, Approved, Received, Refunded
    refund_amount: Decimal

class LoyaltyAccount(Base):
    id: int
    customer_id: int
    points_balance: int
    tier: str  # Gold, Silver, Bronze
```

### Implementation Tips

1. **Real-time Updates**: Order status synced with fulfillment system
2. **Fraud Detection**: Check patterns (excessive returns, amount anomalies)
3. **Email Integration**: Send order confirmations, shipping, returns updates
4. **Currency Handling**: Support multiple currencies
5. **Audit Trail**: Log all transactions for compliance

### Use Cases for E-Commerce Domain

| Use Case | Specialists Needed | Complexity |
|----------|-------------------|-----------|
| Customer support routing | Orders, Returns, Payments | Medium |
| Order processing | Orders | Medium |
| Fraud detection | Payments, Orders | Medium |
| Loyalty program | Loyalty | Medium |

---

## Data Analytics Domain

### Domain Focus

**Purpose**: Enable natural language queries against databases and perform mathematical calculations.

**Key Workflows**:
- Natural language to SQL conversion
- Database query execution
- Mathematical calculations
- Data analysis and reporting
- Dataset exploration

### Specialists Pattern

Data Analytics agents typically use:

```
┌────────────────────┐
│ Analytics Supervisor│
├────────────────────┤
│
├─→ Database Specialist
│   ├─ Schema understanding
│   ├─ SQL generation
│   ├─ Query execution
│   └─ Result formatting
│
└─→ Math Specialist
    ├─ Calculations
    ├─ Statistical analysis
    └─ Percentage operations
```

### Data Schema Patterns

```python
# Typically external datasets, not stored
class QueryCache(Base):
    id: int
    query: str
    result: JSON
    cached_at: DateTime
    expires_at: DateTime

class DataSource(Base):
    id: int
    name: str
    connection_string: str
    schema: JSON  # Tables, columns, types
```

### Implementation Tips

1. **Security**: Validate SQL queries to prevent injection
2. **Performance**: Add query timeouts, result limits
3. **Caching**: Cache schema metadata and frequent queries
4. **Error Messages**: Friendly error handling for bad SQL
5. **Limits**: Restrict to SELECT queries (no modifications)

### Use Cases for Data Analytics Domain

| Use Case | Specialists Needed | Complexity |
|----------|-------------------|-----------|
| Natural language queries | Database | Medium |
| Ad-hoc analysis | Database, Math | Medium |
| Sales analytics | Database | Medium |

---

## DevOps Domain

### Domain Focus

**Purpose**: Automate development operations, repository management, workflow automation, and CI/CD.

**Key Workflows**:
- Repository and file management
- Issue and pull request handling
- Workflow dispatch and automation
- Code search and analysis
- Artifact management
- Commit and branch analysis

### Specialists Pattern

DevOps agents typically use:

```
┌──────────────────┐
│ DevOps Supervisor│
├──────────────────┤
│
├─→ Repository Specialist
│   ├─ Repo info/list
│   ├─ File read/write
│   ├─ Branch management
│   └─ Tag management
│
├─→ Issue Specialist
│   ├─ Issue creation
│   ├─ Issue search
│   ├─ Label management
│   └─ Assignment
│
├─→ PR Specialist
│   ├─ PR creation
│   ├─ PR review
│   ├─ Merge operations
│   └─ Diff analysis
│
├─→ Workflow Specialist
│   ├─ Workflow dispatch
│   ├─ Artifact retrieval
│   ├─ Secrets management
│   └─ Status checks
│
└─→ Code Specialist
    ├─ Code search
    ├─ Commit analysis
    └─ Release notes
```

### Data Schema Patterns

```python
class Repository(Base):
    id: int
    name: str
    url: str
    provider: str  # github, gitlab, bitbucket
    api_token: str  # Encrypted

class Workflow(Base):
    id: int
    repo_id: int
    workflow_name: str
    status: str  # success, failure, pending
    triggered_by: str  # user_id
    triggered_at: DateTime

class Artifact(Base):
    id: int
    workflow_id: int
    name: str
    url: str
    size: int
    expires_at: DateTime
```

### Implementation Tips

1. **Authentication**: Securely store and rotate API tokens
2. **Rate Limiting**: Respect GitHub API rate limits
3. **Webhooks**: Listen to repo events for real-time updates
4. **Async Operations**: Dispatch workflows asynchronously
5. **Audit Logging**: Track all repo modifications

### Use Cases for DevOps Domain

| Use Case | Specialists Needed | Complexity |
|----------|-------------------|-----------|
| Automated PR reviews | PR, Code | Advanced |
| Issue triage | Issue | Advanced |
| Workflow automation | Workflow | Advanced |
| Release automation | Repository, Workflow | Advanced |

---

## Healthcare Domain

### Domain Focus

**Purpose**: Automate healthcare operations including patient management, appointments, billing, and clinical workflows.

**Key Workflows**:
- Patient registration and management
- Appointment booking and scheduling
- Billing and insurance management
- Pharmacy operations
- Lab test ordering and tracking
- Ward and bed management

### Specialists Pattern

Healthcare agents typically use:

```
┌──────────────────────┐
│ Healthcare Supervisor│
├──────────────────────┤
│
├─→ Appointments Specialist
│   ├─ Booking
│   ├─ Rescheduling
│   ├─ Cancellation
│   └─ Reminders
│
├─→ Billing Specialist
│   ├─ Invoice generation
│   ├─ Insurance claims
│   ├─ Payment receipt
│   └─ Reconciliation
│
├─→ Pharmacy Specialist
│   ├─ Prescription processing
│   ├─ Inventory management
│   ├─ Drug interaction check
│   └─ Fulfillment
│
├─→ Lab Specialist
│   ├─ Test ordering
│   ├─ Result tracking
│   ├─ Report generation
│   └─ Abnormal flagging
│
└─→ Ward Specialist
    ├─ Bed assignment
    ├─ Patient transfers
    ├─ Discharge processing
    └─ Inventory tracking
```

### Data Schema Patterns

```python
class Patient(Base):
    id: int
    mrn: str  # Medical Record Number, unique
    name: str
    dob: Date
    gender: str
    insurance_id: str
    contact: str

class Appointment(Base):
    id: int
    patient_id: int
    doctor_id: int
    appointment_date: DateTime
    duration_minutes: int
    status: str  # Scheduled, Completed, Cancelled, NoShow
    notes: str

class Prescription(Base):
    id: int
    patient_id: int
    doctor_id: int
    medication: str
    dosage: str
    quantity: int
    refills: int
    issued_at: DateTime
    status: str  # Active, Filled, Expired, Cancelled

class Billing(Base):
    id: int
    patient_id: int
    amount: Decimal
    service_date: DateTime
    insurance_claim_id: str
    status: str  # Pending, Billed, Paid, Appealed
```

### Implementation Tips

1. **HIPAA Compliance**: Encrypt sensitive data, audit access
2. **Data Privacy**: Implement strict access controls
3. **Integration**: Connect to EHR, insurance systems, pharmacies
4. **Scheduling**: Handle timezone-aware appointments
5. **Notifications**: SMS/email reminders for patients

### Use Cases for Healthcare Domain

| Use Case | Specialists Needed | Complexity |
|----------|-------------------|-----------|
| Patient management | Appointments, Pharmacy | Advanced |
| Billing operations | Billing | Advanced |
| Lab operations | Lab | Advanced |
| Hospital operations | All specialists | Advanced |

---

## Human Resources Domain

### Domain Focus

**Purpose**: Automate HR operations including recruitment, candidate management, onboarding, and analytics.

**Key Workflows**:
- Job posting and management
- Resume screening and evaluation
- Interview scheduling and feedback
- Offer creation and tracking
- Onboarding process management
- Employee analytics and reporting

### Specialists Pattern

HR agents typically use:

```
┌──────────────────┐
│ HR Supervisor    │
├──────────────────┤
│
├─→ Jobs Specialist
│   ├─ Job posting
│   ├─ Job description management
│   ├─ Application tracking
│   └─ Candidate pool
│
├─→ Resumes Specialist
│   ├─ Resume parsing
│   ├─ Skill extraction
│   ├─ Experience validation
│   └─ Screening scoring
│
├─→ Interviews Specialist
│   ├─ Interview scheduling
│   ├─ Feedback collection
│   ├─ Scoring
│   └─ Decision tracking
│
├─→ Offers Specialist
│   ├─ Offer generation
│   ├─ Offer tracking
│   ├─ Acceptance management
│   └─ Onboarding initiation
│
└─→ Analytics Specialist
    ├─ Hiring metrics
    ├─ Time-to-hire
    ├─ Diversity reporting
    └─ Funnel analysis
```

### Data Schema Patterns

```python
class JobPosting(Base):
    id: int
    position_title: str
    department: str
    salary_range: str
    posted_at: DateTime
    status: str  # Open, Closed, Filled

class Candidate(Base):
    id: int
    name: str
    email: str
    phone: str
    resume_url: str
    resume_text: str  # Extracted text
    skills: List[str]
    experience_years: int

class Interview(Base):
    id: int
    candidate_id: int
    job_id: int
    interview_date: DateTime
    interviewer_id: int
    score: int
    feedback: str
    decision: str  # Pass, Fail, Maybe

class Offer(Base):
    id: int
    candidate_id: int
    job_id: int
    salary: Decimal
    start_date: Date
    status: str  # Pending, Accepted, Rejected
```

### Implementation Tips

1. **Resume Parsing**: Use OCR or API services
2. **Session Memory**: Store candidate conversations across interactions
3. **Workflow States**: Track candidate journey through pipeline
4. **Notifications**: Send interview invites and offer letters
5. **Analytics**: Calculate metrics like time-to-hire, conversion rates

### Use Cases for HR Domain

| Use Case | Specialists Needed | Complexity |
|----------|-------------------|-----------|
| Job applicant screening | Resumes | Medium |
| Interview coordination | Interviews | Medium |
| Offer management | Offers | Medium |
| Hiring analytics | Analytics | Medium |

---

## Business Intelligence Domain

### Domain Focus

**Purpose**: Automate analytics and reporting, providing insights into sales, products, and business performance.

**Key Workflows**:
- Sales data analysis
- Product performance reporting
- Revenue analysis and forecasting
- Top performers identification
- Business intelligence dashboards

### Specialists Pattern

BI agents typically use a simpler pattern:

```
┌──────────────────┐
│ BI Supervisor    │
├──────────────────┤
│
└─→ Analytics Specialist
    ├─ Sales analysis
    ├─ Genre filtering
    ├─ Product ranking
    ├─ Revenue calculation
    └─ Reporting
```

### Data Schema Patterns

```python
# Typically external CSVs or databases
class SalesRecord(Base):
    id: int
    product_id: int
    quantity: int
    unit_price: Decimal
    sale_date: Date
    region: str

class ProductMetrics(Base):
    id: int
    product_id: int
    total_sales: Decimal
    units_sold: int
    rating: float
    category: str
```

### Implementation Tips

1. **Simple Architecture**: Often single-specialist design
2. **Data Loading**: Efficient CSV/database loading
3. **Aggregations**: Pre-compute summaries for performance
4. **Filtering**: Support multiple filter dimensions
5. **Exports**: Enable report download (PDF, Excel)

### Use Cases for BI Domain

| Use Case | Specialists Needed | Complexity |
|----------|-------------------|-----------|
| Sales reporting | Analytics | Easy |
| Product analytics | Analytics | Easy |
| Revenue analysis | Analytics | Easy |

---

## Education Domain

### Domain Focus

**Purpose**: Automate academic operations including enrollment, course management, grading, and student services.

**Key Workflows**:
- Student registration and enrollment
- Course management and scheduling
- Grade tracking and transcript generation
- Degree audits and requirement validation
- Class scheduling and conflict detection
- Academic advising and at-risk student detection

### Specialists Pattern

Education agents typically use:

```
┌──────────────────────┐
│ Education Supervisor │
├──────────────────────┤
│
├─→ Registration Specialist
│   ├─ Student enrollment
│   ├─ De-registration
│   ├─ Transfer processing
│   └─ Status tracking
│
├─→ Courses Specialist
│   ├─ Course setup
│   ├─ Capacity management
│   ├─ Waitlist handling
│   └─ Prerequisite checking
│
├─→ Grades Specialist
│   ├─ Grade entry
│   ├─ Transcript generation
│   ├─ GPA calculation
│   └─ Academic standing
│
├─→ Advising Specialist
│   ├─ Degree audit
│   ├─ Requirement validation
│   ├─ At-risk identification
│   └─ Recommendations
│
└─→ Scheduling Specialist
    ├─ Class scheduling
    ├─ Conflict detection
    ├─ Room assignment
    └─ Faculty allocation
```

### Data Schema Patterns

```python
class Student(Base):
    id: int
    student_id: str  # Unique student ID
    name: str
    email: str
    program_id: int
    enrollment_date: Date
    status: str  # Active, Graduated, Suspended

class Course(Base):
    id: int
    code: str  # e.g., CS101
    name: str
    credits: int
    capacity: int
    current_enrollment: int
    semester: str
    prerequisites: List[str]

class Enrollment(Base):
    id: int
    student_id: int
    course_id: int
    enrollment_date: DateTime
    grade: str  # A, B, C, etc.
    status: str  # Active, Dropped, Completed

class DegreeRequirement(Base):
    id: int
    program_id: int
    requirement_name: str
    course_ids: List[int]
    credit_hours: int
    sequence: int  # Order
```

### Implementation Tips

1. **Prerequisite Checking**: Validate course eligibility
2. **Conflict Detection**: Prevent scheduling conflicts
3. **GPA Calculation**: Accurate cumulative and term GPA
4. **At-Risk Detection**: Identify struggling students
5. **Integration**: Connect to student information systems (SIS)

### Use Cases for Education Domain

| Use Case | Specialists Needed | Complexity |
|----------|-------------------|-----------|
| Student enrollment | Registration, Courses | Advanced |
| Grade management | Grades | Advanced |
| Degree audits | Advising | Advanced |
| Academic advising | Advising, Courses | Advanced |

---

## Cross-Domain Patterns

### Shared Patterns Across All Domains

While each domain is specialized, all follow these common patterns:

#### 1. RBAC (Role-Based Access Control)

```python
# All domains implement role-based access
ROLE_PERMISSIONS = {
    "admin": ["create", "read", "update", "delete"],
    "manager": ["create", "read", "update"],
    "analyst": ["read"],
    "user": ["read"],
}
```

#### 2. Audit Logging

```python
# All operations logged
def log_operation(operation: str, resource: str, user_id: str, result: str):
    log_entry = {
        "timestamp": datetime.utcnow(),
        "operation": operation,
        "resource": resource,
        "user_id": user_id,
        "result": result
    }
    # Store in database or external service
```

#### 3. Error Handling

```python
# Graceful error responses across all domains
try:
    result = await execute_operation()
except ValidationError as e:
    return {"error": str(e), "code": "VALIDATION_ERROR"}
except ExternalServiceError as e:
    return {"error": "Service unavailable", "code": "SERVICE_ERROR"}
```

#### 4. State Management

```python
# All use LangGraph for orchestration
from langgraph.graph import StateGraph

graph = StateGraph(AgentState)
# Add nodes, edges, compile
```

#### 5. Data Persistence

```python
# All use PostgreSQL + SQLAlchemy
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)
```

---

## Choosing a Domain

### Decision Matrix

| Requirement | Best Domain | Alternative |
|------------|------------|------------|
| Financial operations | Finance | Business Intelligence |
| Security & compliance | Cybersecurity | DevOps |
| Customer support | E-Commerce | Human Resources |
| Data analysis | Data Analytics | Business Intelligence |
| CI/CD automation | DevOps | N/A |
| Hospital/clinic ops | Healthcare | N/A |
| Recruitment | Human Resources | E-Commerce |
| Sales reporting | Business Intelligence | Data Analytics |
| Academic operations | Education | Data Analytics |

### Getting Started

1. **Identify your domain** using the matrix above
2. **Read the domain section** in this guide
3. **Review the agent README** in the domain folder
4. **Study the specialists pattern** for your domain
5. **See QUICK_START.md** for setup instructions
6. **Refer to ARCHITECTURE.md** for technical deep dives

---

## Summary

Each domain provides:

✅ **Proven Specialists Pattern** - Tailored routing logic  
✅ **Domain-Specific Data Models** - Optimized schemas  
✅ **Industry Best Practices** - Security, compliance, etc.  
✅ **Reusable Implementation** - Copy, adapt, extend  
✅ **Production-Ready Code** - Battle-tested patterns  

For technical implementation, refer to ARCHITECTURE.md. For setup steps, see QUICK_START.md.
