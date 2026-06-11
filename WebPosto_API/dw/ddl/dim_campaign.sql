-- dim_campaign — F04.5
CREATE TABLE IF NOT EXISTS dim_campaign (
    campaign_sk                 INTEGER PRIMARY KEY AUTOINCREMENT,
    campaign_id                 TEXT NOT NULL UNIQUE,
    campaign_name               TEXT NOT NULL,
    goal_type                   TEXT NOT NULL,
    weight                      REAL NOT NULL DEFAULT 1
);

-- dim_goal_type — F04.5
CREATE TABLE IF NOT EXISTS dim_goal_type (
    goal_type_sk                INTEGER PRIMARY KEY AUTOINCREMENT,
    goal_type                   TEXT NOT NULL UNIQUE,
    unit                        TEXT,
    higher_is_better            INTEGER NOT NULL DEFAULT 1
);
