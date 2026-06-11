# Architecture Readiness

{
  "services": [
    "corporate_intelligence_hub_service",
    "executive_scorecard_service",
    "benchmark_intelligence_service",
    "operator_performance / people_intelligence",
    "executive_decision_engine_service",
    "action_center_service",
    "goals_campaign_engine_service",
    "executive_coverage_recovery_service"
  ],
  "snapshots": [
    "corporate_hub",
    "decision_engine",
    "action_center",
    "executive_scorecard",
    "benchmark",
    "people",
    "goals"
  ],
  "apis": [
    {
      "path": "/api/v1/corporate-hub/cockpit",
      "domain": "corporate_hub"
    },
    {
      "path": "/api/v1/executive-scorecard/cockpit",
      "domain": "executive_scorecard"
    },
    {
      "path": "/api/v1/benchmark/cockpit",
      "domain": "benchmark"
    },
    {
      "path": "/api/v1/people-intelligence/cockpit",
      "domain": "people"
    },
    {
      "path": "/api/v1/goals-campaigns/cockpit",
      "domain": "goals"
    },
    {
      "path": "/api/v1/executive-decision/cockpit",
      "domain": "decision_engine"
    },
    {
      "path": "/api/v1/action-center/cockpit",
      "domain": "action_center"
    },
    {
      "path": "/api/v1/data-trust/recovery/cockpit",
      "domain": "d05"
    }
  ],
  "proibido": [
    "WebPosto live",
    "Postgres operacional direto"
  ]
}
