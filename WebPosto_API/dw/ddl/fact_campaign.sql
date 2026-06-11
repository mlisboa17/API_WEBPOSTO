-- fact_campaign — F04.5
CREATE TABLE IF NOT EXISTS fact_campaign (
    campaign_sk                 INTEGER PRIMARY KEY AUTOINCREMENT,
    date_sk                     INTEGER,
    campaign_id                 TEXT NOT NULL,
    campaign_name               TEXT NOT NULL,
    status                      TEXT NOT NULL,
    percentual_medio            REAL NOT NULL DEFAULT 0,
    roi_campanha                REAL NOT NULL DEFAULT 0,
    loaded_at                   TEXT NOT NULL DEFAULT (datetime('now'))
);
