# Azure DevOps Automated Rollback Engine

## Overview

The Azure DevOps Automated Rollback Engine is a Python-based automation solution designed to identify, validate, and revert code changes associated with Azure DevOps User Stories.

The solution traces User Stories to linked Pull Requests, extracts associated commits, performs controlled Git revert operations, validates repository state using SHA-256 hashing, creates a dedicated rollback branch, and generates audit logs for complete traceability.

---

## Objective

The objective of this solution is to automate rollback activities by:

- Identifying Pull Requests linked to Azure DevOps User Stories
- Extracting associated commit IDs
- Reverting commits automatically
- Validating repository state using SHA-256
- Creating rollback branches
- Maintaining audit logs
- Reducing manual rollback effort

---
## Solution Architecture

```mermaid
flowchart LR

subgraph Source Systems
    ADO[Azure DevOps]
    GH[GitHub Repository]
end

subgraph Rollback Automation Framework
    PR[PR Discovery]
    CM[Commit Extraction]
    SHA1[SHA256 Before]
    REV[Commit Reversion]
    SHA2[SHA256 After]
    VAL[State Validation]
    RB[Rollback Branch]
    RPR[Create Review Pull Request]
    APP[Developer Approval]
    MERGE[Merge to Main]
    AUD[Audit Logging]
end

ADO --> PR
PR --> CM

GH --> SHA1
CM --> REV

SHA1 --> REV
REV --> SHA2
SHA2 --> VAL

VAL --> RB
RB --> RPR
RPR --> APP
APP --> MERGE

MERGE --> AUD
```
---
## Description

The Rollback Engine automates the rollback of Azure DevOps work items by identifying the associated pull requests and commits, generating reverse commits, and creating a dedicated rollback branch. A pull request is then created for developer review and approval before the rollback is merged into the main branch. The solution also generates audit logs and rollback reports to provide traceability, validation, and clear visibility into the rollback process.

---

## Sequence Diagram

```mermaid
sequenceDiagram

box Azure DevOps
participant ADO as User Story
end

box Rollback Engine
participant PR as PR Discovery
participant REV as Revert Engine
participant SHA as SHA Validator
participant LOG as Audit Logger
end

box GitHub
participant GH as Repository
participant RB as Rollback Branch
participant DPR as Developer
end

ADO->>PR: Submit Work Item ID

PR->>ADO: Fetch Linked Pull Request
ADO-->>PR: PR Details

PR->>ADO: Fetch Commit IDs
ADO-->>PR: Commit List

REV->>GH: Clone Repository
GH-->>REV: Repository Copy

REV->>SHA: Generate SHA256 Before
SHA-->>REV: Hash

REV->>GH: Revert Commits
GH-->>REV: Success

REV->>SHA: Generate SHA256 After
SHA-->>REV: Hash

REV->>SHA: Validate Repository
SHA-->>REV: Validation Passed

REV->>RB: Create Rollback Branch

RB->>GH: Push Rollback Branch

GH->>DPR: Create Review Pull Request
DPR-->>GH: Review & Approve

GH->>GH: Merge Rollback Branch to Main

REV->>LOG: Generate Audit Log
LOG-->>ADO: Rollback Summary
```
---

## Technology Stack

| Component | Technology |
|------------|------------|
| Language | Python 3.x |
| Work Item Management | Azure DevOps |
| Source Control | GitHub |
| Version Control | Git |
| Validation | SHA-256 |
| Logging | Python Logging |
| Authentication | Azure DevOps PAT |
| APIs | Azure DevOps REST APIs |

---


## Error Handling & Edge Cases

### 1. Consecutive Commits

**Scenario**

Multiple commits belong to the same feature implementation.

**Handling**

- Revert commits in reverse order
- Preserve dependency chain
- Maintain repository consistency

---

### 2. Non-Consecutive Commits

**Scenario**

User Story changes are spread across unrelated commits.

**Handling**

- Process commits individually
- Maintain rollback order
- Validate repository state after rollback

---

### 3. Merge Conflicts

**Scenario**

Rollback overlaps with newer code changes.

**Handling**

- Stop execution immediately
- Log conflict details
- Require manual intervention

---

### 4. Branch Not Found

**Scenario**

Target branch does not exist.

**Handling**

- Validate branch existence before execution
- Abort rollback safely

---

### 5. Pull Request Not Found

**Scenario**

User Story has no linked Pull Requests.

**Handling**

- Exit gracefully
- Log validation failure

---

### 6. Commit Not Found

**Scenario**

Commit referenced by Pull Request is unavailable.

**Handling**

- Validate commit existence
- Skip processing and log error

---

### 7. Repository Access Failure

**Scenario**

GitHub clone or authentication failure.

**Handling**

- Stop execution
- Capture detailed error logs

---

## Sample Execution Flow

```text
========== PIPELINE STARTED ==========

Work Item ID: 14

Pull Requests Found: 2

Commits Identified:
a12b34c
d45e67f

SHA256 Before:
7f6a8e9d...

Reverting Commit:
d45e67f

Reverting Commit:
a12b34c

SHA256 After:
4d9e1f2a...

Repository Validation:
SUCCESS

Rollback Branch Created:
rollback-US14

Changes Pushed Successfully

========== PIPELINE COMPLETED ==========
```

---

## Benefits

- Automated rollback execution
- Reduced recovery time
- Improved deployment reliability
- Complete auditability
- Repository integrity validation
- Reduced manual effort
- Scalable rollback process

=======
---

## Project Status

### Current POC Scope

✅ Azure DevOps User Story Integration

✅ Pull Request Discovery

✅ Commit Extraction

✅ Git Revert Automation

✅ SHA-256 Validation

✅ Rollback Branch Creation

✅ GitHub Push Automation

✅ Audit Logging

✅ Common Error Handling

---

## Author

**Veeresh**
