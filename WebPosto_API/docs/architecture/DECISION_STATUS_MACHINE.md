---
# 🔀 DECISION STATUS MACHINE | LOGOS Architecture
# Type: ARCHITECTURE_SPEC
# Version: 1.0
# Sprint: EXEC-01 — Decision Execution Platform
# Status: IMPLEMENTED
---

# Decision Status Machine

> **State machine for managing decision lifecycle with strict transitions, timestamps, and audit trail.**

---

## 🎯 Purpose

Ensures:
- Valid state transitions only
- Complete audit trail (timestamps + actors)
- Automatic expiration and archival
- No orphaned decisions

---

## 📊 State Diagram

```
                    ┌─────────────────┐
                    │      NEW        │
                    │  (generated)    │
                    └────────┬────────┘
                             │
           ┌─────────────────┼─────────────────┐
           │                 │                 │
           ▼                 ▼                 ▼
    ┌─────────────┐   ┌─────────────┐   ┌─────────────┐
    │    READY    │   │  CANCELLED  │   │  EXPIRED    │
    │(presented)  │   │(cancelled)  │   │(auto-expire)│
    └──────┬──────┘   └──────┬──────┘   └──────┬──────┘
           │                  │                  │
           │                  └────────┬─────────┘
           │                           │
           ▼                           ▼
    ┌─────────────┐             ┌─────────────┐
    │  EXECUTING  │             │  ARCHIVED   │
    │(executing)  │             │ (archived) │
    └──────┬──────┘             └─────────────┘
           │
     ┌─────┼─────┬─────────────┐
     │     │     │             │
     ▼     ▼     ▼             ▼
┌────────┐ │ ┌────────┐   ┌────────┐
│COMPLETED│ │ │ NOT_   │   │PARTIAL │
│(success)│ │ │COMPLETED│   │(partial)│
└───┬─────┘ │ └───┬────┘   └───┬────┘
    │       │     │            │
    └───────┼─────┴────────────┘
            │
            ▼
     ┌─────────────┐
     │  ARCHIVED   │
     │  (archived) │
     └─────────────┘
```

---

## 📋 States

| State | Code | Description | Entry Action | Exit Actions |
|-------|------|-------------|--------------|--------------|
| **NEW** | `new` | Decision created, not yet presented | - | present() |
| **READY** | `ready` | Presented to owner, awaiting execution | Add READY event | start_execution(), expire(), cancel() |
| **EXECUTING** | `executing` | Owner clicked "Execute Now" | Add EXECUTING event | complete(), mark_not_completed(), mark_partial() |
| **COMPLETED** | `completed` | Action fully completed | Add COMPLETED event | archive() |
| **NOT_COMPLETED** | `not_completed` | Action not completed | Add NOT_COMPLETED event | archive() |
| **PARTIAL** | `partial` | Action partially completed | Add PARTIAL event | archive() |
| **EXPIRED** | `expired` | Expired (> 7 days) | Add EXPIRED event | archive() |
| **CANCELLED** | `cancelled` | Cancelled before execution | Add CANCELLED event | archive() |
| **ARCHIVED** | `archived` | Terminal state archived | Add ARCHIVED event | - |

---

## 🔄 Valid Transitions

| From | To | Condition | Required Fields |
|------|----|-----------|-----------------|
| NEW | READY | Decision presented | decision_title, estimated_impact |
| NEW | CANCELLED | Decision cancelled | cancellation_reason |
| READY | EXECUTING | Owner starts execution | action_type |
| READY | EXPIRED | > 7 days without action | is_expired() == True |
| READY | CANCELLED | Owner/system cancels | - |
| EXECUTING | COMPLETED | Execution successful | confirmation (SIM) |
| EXECUTING | NOT_COMPLETED | Execution failed | confirmation (NÃO) |
| EXECUTING | PARTIAL | Partial completion | confirmation (PARCIAL) |
| COMPLETED | ARCHIVED | Auto after 30 days | - |
| NOT_COMPLETED | ARCHIVED | Auto after 30 days | - |
| PARTIAL | ARCHIVED | Auto after 30 days | - |
| EXPIRED | ARCHIVED | Auto after 7 days | - |
| CANCELLED | ARCHIVED | Auto after 7 days | - |

---

## ⏰ Automatic Transitions

### Expiration

```python
# Check every hour
if status == READY and (now - ready_timestamp) > 7 days:
    transition(READY → EXPIRED)
```

### Archival

```python
# Check daily
if status in [COMPLETED, NOT_COMPLETED, PARTIAL] and (now - terminal_timestamp) > 30 days:
    transition(terminal → ARCHIVED)

if status in [EXPIRED, CANCELLED] and (now - terminal_timestamp) > 7 days:
    transition(terminal → ARCHIVED)
```

---

## 📝 Event Structure

```python
class TimelineEvent:
    event_id: UUID          # Unique identifier
    timestamp: datetime     # UTC
    status: DecisionStatus  # New status
    actor: str             # 'system' | 'user' | 'auto'
    action: str            # Description
    metadata: Dict         # Additional context
```

### Example Events

```json
[
  {
    "event_id": "evt_001",
    "timestamp": "2026-06-29T08:10:00Z",
    "status": "new",
    "actor": "system",
    "action": "Decision created by MoneyAtRiskEngine",
    "metadata": {
      "source_engine": "MoneyAtRiskEngine",
      "estimated_impact": 8500.00
    }
  },
  {
    "event_id": "evt_002",
    "timestamp": "2026-06-29T08:12:00Z",
    "status": "ready",
    "actor": "system",
    "action": "Decision presented to owner",
    "metadata": {
      "presented_to": "user_001"
    }
  },
  {
    "event_id": "evt_003",
    "timestamp": "2026-06-29T09:05:00Z",
    "status": "executing",
    "actor": "user",
    "action": "Owner clicked 'Execute Now'",
    "metadata": {
      "user_id": "user_001",
      "ip_address": "192.168.1.1"
    }
  },
  {
    "event_id": "evt_004",
    "timestamp": "2026-06-29T09:12:00Z",
    "status": "completed",
    "actor": "user",
    "action": "Execution confirmed with SIM result",
    "metadata": {
      "confirmation_id": "conf_001",
      "confirmed_amount": 8500.00,
      "user_id": "user_001"
    }
  }
]
```

---

## 🏗️ Implementation

### StateMachine Class

```python
class DecisionStatusMachine:
    TRANSITIONS: Dict[Tuple[Status, Status], TransitionRule]
    
    @classmethod
    def can_transition(record, to_status) -> Tuple[bool, Optional[str]]:
        # Check if transition is valid
        # Validate required fields
        # Run custom validators
        
    @classmethod
    def transition(record, to_status, actor, action, metadata) -> ExecutionRecord:
        # Validate
        # Update status
        # Add timeline event
        # Persist
        
    # Convenience methods
    @classmethod
    def present(record) -> ExecutionRecord
    
    @classmethod
    def start_execution(record, user_id) -> ExecutionRecord
    
    @classmethod
    def complete(record, confirmation_id, user_id) -> ExecutionRecord
    
    @classmethod
    def expire(record) -> ExecutionRecord
    
    @classmethod
    def archive(record) -> ExecutionRecord
```

### TransitionRule

```python
@dataclass
class TransitionRule:
    from_status: DecisionStatus
    to_status: DecisionStatus
    required_fields: List[str]
    validator: Optional[Callable]
    auto_archive_after_days: Optional[int]
```

---

## 🎨 State Visualization

### Badge Colors

| State | Color | Hex |
|-------|-------|-----|
| NEW | Gray | #6B7280 |
| READY | Blue | #3B82F6 |
| EXECUTING | Yellow | #F59E0B |
| COMPLETED | Green | #10B981 |
| NOT_COMPLETED | Red | #EF4444 |
| PARTIAL | Orange | #F97316 |
| EXPIRED | Gray | #9CA3AF |
| CANCELLED | Gray | #9CA3AF |
| ARCHIVED | Light Gray | #D1D5DB |

### State Icons

| State | Icon |
|-------|------|
| NEW | ⭕ |
| READY | 🔵 |
| EXECUTING | 🟡 |
| COMPLETED | ✅ |
| NOT_COMPLETED | ❌ |
| PARTIAL | ⚠️ |
| EXPIRED | ⏰ |
| CANCELLED | 🚫 |
| ARCHIVED | 📦 |

---

## 📊 Metrics from State Machine

### Calculable Metrics

| Metric | Calculation |
|--------|-------------|
| Time to Execute | READY timestamp → EXECUTING timestamp |
| Execution Duration | EXECUTING timestamp → terminal timestamp |
| Time to Archive | Terminal timestamp → ARCHIVED timestamp |
| Expiration Rate | EXPIRED count / READY count |
| Completion Rate | COMPLETED count / EXECUTING count |
| Success Rate | (COMPLETED + PARTIAL) / EXECUTING count |

---

## 🔒 Validation Rules

### Required Fields by Transition

```python
TRANSITION_REQUIREMENTS = {
    (NEW, READY): ["decision_title", "estimated_impact"],
    (NEW, CANCELLED): ["cancellation_reason"],
    (READY, EXECUTING): ["action_type"],
    (READY, EXPIRED): [],  # Validated by is_expired()
    (EXECUTING, COMPLETED): ["confirmation"],
    (EXECUTING, NOT_COMPLETED): ["confirmation"],
    (EXECUTING, PARTIAL): ["confirmation"],
}
```

### Custom Validators

```python
VALIDATORS = {
    (READY, EXPIRED): lambda record: record.is_expired(),
}
```

---

## 🧪 Testing Scenarios

### Happy Path
```
NEW → READY → EXECUTING → COMPLETED → ARCHIVED
```

### Expiration Path
```
NEW → READY → [7 days pass] → EXPIRED → ARCHIVED
```

### Cancellation Path
```
NEW → READY → CANCELLED → ARCHIVED
```

### Partial Path
```
NEW → READY → EXECUTING → PARTIAL → [follow-up] → COMPLETED → ARCHIVED
```

### Invalid Transitions (Should Fail)
```
NEW → COMPLETED          # ❌ Must go through EXECUTING
READY → ARCHIVED         # ❌ Must go through terminal state
EXECUTING → READY        # ❌ Cannot go back
COMPLETED → EXECUTING    # ❌ Cannot restart
```

---

**[DECISION STATUS MACHINE — Architecture]**

*Status: IMPLEMENTED | States: 9 | Transitions: 11 | Auto-transitions: 2*
