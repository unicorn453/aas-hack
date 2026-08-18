-- EDC PostgreSQL schema for tractusx-edc 0.7.3
-- Cumulative final state of all Flyway migrations.
-- Safe to run on an existing DB (all statements use IF NOT EXISTS).

-- ============================================================
-- LEASE  (shared dependency for all state-machine stores)
-- ============================================================
CREATE TABLE IF NOT EXISTS edc_lease
(
    leased_by      VARCHAR(255) NOT NULL,
    leased_at      BIGINT,
    lease_duration INTEGER      DEFAULT 60000 NOT NULL,
    lease_id       VARCHAR(255) NOT NULL
        CONSTRAINT lease_pk PRIMARY KEY
);
COMMENT ON COLUMN edc_lease.leased_at IS 'posix timestamp of lease';
COMMENT ON COLUMN edc_lease.lease_duration IS 'duration of lease in milliseconds';

CREATE UNIQUE INDEX IF NOT EXISTS lease_lease_id_uindex ON edc_lease (lease_id);

-- ============================================================
-- TRANSFER PROCESS
-- ============================================================
CREATE TABLE IF NOT EXISTS edc_transfer_process
(
    id                       VARCHAR(255) NOT NULL
        CONSTRAINT transfer_process_pk PRIMARY KEY,
    type                     VARCHAR(255) NOT NULL,
    state                    INTEGER      NOT NULL,
    state_count              INTEGER      DEFAULT 0   NOT NULL,
    state_time_stamp         BIGINT,
    created_at               BIGINT       DEFAULT 0   NOT NULL,
    updated_at               BIGINT       DEFAULT 0   NOT NULL,
    trace_context            TEXT,
    error_detail             TEXT,
    resource_manifest        TEXT,
    provisioned_resource_set TEXT,
    content_data_address     TEXT,
    deprovisioned_resources  TEXT,
    private_properties       TEXT,
    callback_addresses       TEXT,
    pending                  BOOLEAN      DEFAULT FALSE,
    transfer_type            VARCHAR(255),
    protocol_messages        TEXT,
    data_plane_id            VARCHAR(255),
    lease_id                 VARCHAR(255)
        CONSTRAINT transfer_process_lease_lease_id_fk
            REFERENCES edc_lease ON DELETE SET NULL
);
COMMENT ON COLUMN edc_transfer_process.trace_context IS 'Java Map serialized as JSON';
COMMENT ON COLUMN edc_transfer_process.resource_manifest IS 'ResourceManifest serialized as JSON';
COMMENT ON COLUMN edc_transfer_process.provisioned_resource_set IS 'ProvisionedResourceSet serialized as JSON';

CREATE UNIQUE INDEX IF NOT EXISTS transfer_process_id_uindex ON edc_transfer_process (id);

-- ============================================================
-- ASSET
-- ============================================================
CREATE TABLE IF NOT EXISTS edc_asset
(
    asset_id           VARCHAR(255) NOT NULL
        CONSTRAINT asset_pk PRIMARY KEY,
    created_at         BIGINT       NOT NULL,
    properties         TEXT,
    private_properties TEXT,
    data_address       TEXT
);

CREATE UNIQUE INDEX IF NOT EXISTS asset_id_uindex ON edc_asset (asset_id);

-- ============================================================
-- POLICY DEFINITION
-- ============================================================
CREATE TABLE IF NOT EXISTS edc_policydefinitions
(
    policy_id             VARCHAR(255) NOT NULL
        CONSTRAINT policydefinitions_pk PRIMARY KEY,
    permissions           TEXT,
    prohibitions          TEXT,
    duties                TEXT,
    extensible_properties TEXT,
    inherits_from         VARCHAR(255),
    assigner              VARCHAR(255),
    assignee              VARCHAR(255),
    target                VARCHAR(255),
    policy_type           VARCHAR(255) NOT NULL DEFAULT 'SET',
    private_properties    TEXT,
    created_at            BIGINT       NOT NULL
);

CREATE UNIQUE INDEX IF NOT EXISTS policy_id_uindex ON edc_policydefinitions (policy_id);

-- ============================================================
-- CONTRACT DEFINITION
-- ============================================================
CREATE TABLE IF NOT EXISTS edc_contract_definitions
(
    created_at             BIGINT       NOT NULL,
    contract_definition_id VARCHAR(255) NOT NULL
        CONSTRAINT contract_definition_pk PRIMARY KEY,
    access_policy_id       VARCHAR(255) NOT NULL,
    contract_policy_id     VARCHAR(255) NOT NULL,
    assets_selector        TEXT,
    private_properties     TEXT,
    validity               BIGINT       DEFAULT 31536000
);

CREATE UNIQUE INDEX IF NOT EXISTS contract_definition_id_uindex ON edc_contract_definitions (contract_definition_id);

-- ============================================================
-- CONTRACT AGREEMENT
-- ============================================================
CREATE TABLE IF NOT EXISTS edc_contract_agreement
(
    agr_id             VARCHAR(255) NOT NULL
        CONSTRAINT contract_agreement_pk PRIMARY KEY,
    provider_agent_id  VARCHAR(255),
    consumer_agent_id  VARCHAR(255),
    signing_date       BIGINT,
    start_date         BIGINT,
    end_date           BIGINT,
    asset_id           VARCHAR(255) NOT NULL,
    policy             TEXT
);

CREATE UNIQUE INDEX IF NOT EXISTS contract_agreement_id_uindex ON edc_contract_agreement (agr_id);

-- ============================================================
-- CONTRACT NEGOTIATION
-- ============================================================
CREATE TABLE IF NOT EXISTS edc_contract_negotiation
(
    id                   VARCHAR(255) NOT NULL
        CONSTRAINT contract_negotiation_pk PRIMARY KEY,
    created_at           BIGINT       NOT NULL,
    updated_at           BIGINT       NOT NULL,
    correlation_id       VARCHAR(255),
    counterparty_id      VARCHAR(255) NOT NULL,
    counterparty_address VARCHAR(255) NOT NULL,
    protocol             VARCHAR(255) NOT NULL,
    type                 VARCHAR(255) NOT NULL,
    state                INTEGER      NOT NULL,
    state_count          INTEGER      DEFAULT 0 NOT NULL,
    state_timestamp      BIGINT,
    error_detail         VARCHAR(255),
    agreement_id         VARCHAR(255),
    contract_offers      TEXT,
    callback_addresses   TEXT,
    trace_context        TEXT,
    pending              BOOLEAN      DEFAULT FALSE,
    protocol_messages    TEXT,
    lease_id             VARCHAR(255)
        CONSTRAINT contract_negotiation_lease_lease_id_fk
            REFERENCES edc_lease ON DELETE SET NULL
);

CREATE UNIQUE INDEX IF NOT EXISTS contract_negotiation_id_uindex ON edc_contract_negotiation (id);
CREATE UNIQUE INDEX IF NOT EXISTS contract_negotiation_agreement_id_uindex ON edc_contract_negotiation (agreement_id);

-- ============================================================
-- EDR INDEX
-- ============================================================
CREATE TABLE IF NOT EXISTS edc_edr_entry
(
    transfer_process_id     VARCHAR(255) NOT NULL
        CONSTRAINT edr_entry_pk PRIMARY KEY,
    agreement_id            VARCHAR(255) NOT NULL,
    asset_id                VARCHAR(255) NOT NULL,
    provider_id             VARCHAR(255) NOT NULL,
    contract_negotiation_id VARCHAR(255),
    created_at              BIGINT       NOT NULL,
    edr_id                  VARCHAR(255) NOT NULL
);

-- ============================================================
-- BPN STORE
-- ============================================================
CREATE TABLE IF NOT EXISTS edc_bpn_stored_group
(
    bpn    VARCHAR(255) NOT NULL
        CONSTRAINT bpn_stored_group_pk PRIMARY KEY,
    groups TEXT
);

-- ============================================================
-- DATA PLANE
-- ============================================================
CREATE TABLE IF NOT EXISTS edc_data_plane
(
    process_id        VARCHAR NOT NULL PRIMARY KEY,
    state             INTEGER NOT NULL,
    created_at        BIGINT  NOT NULL,
    updated_at        BIGINT  NOT NULL,
    state_count       INTEGER DEFAULT 0 NOT NULL,
    state_time_stamp  BIGINT,
    trace_context     JSON,
    error_detail      VARCHAR,
    callback_address  VARCHAR,
    lease_id          VARCHAR
        CONSTRAINT data_plane_lease_lease_id_fk
            REFERENCES edc_lease ON DELETE SET NULL,
    source            JSON,
    destination       JSON,
    properties        JSON,
    flow_type         VARCHAR
);
COMMENT ON COLUMN edc_data_plane.trace_context IS 'Java Map serialized as JSON';
COMMENT ON COLUMN edc_data_plane.source IS 'DataAddress serialized as JSON';
COMMENT ON COLUMN edc_data_plane.destination IS 'DataAddress serialized as JSON';
COMMENT ON COLUMN edc_data_plane.properties IS 'Java Map serialized as JSON';

-- ============================================================
-- POLICY MONITOR
-- ============================================================
CREATE TABLE IF NOT EXISTS edc_policy_monitor
(
    entry_id        VARCHAR(255) NOT NULL
        CONSTRAINT policy_monitor_pk PRIMARY KEY,
    state           INTEGER      NOT NULL,
    state_count     INTEGER      DEFAULT 0 NOT NULL,
    state_timestamp BIGINT,
    error_detail    TEXT,
    contract_id     VARCHAR(255) NOT NULL,
    policy          TEXT,
    created_at      BIGINT       NOT NULL,
    updated_at      BIGINT       NOT NULL,
    trace_context   TEXT,
    pending         BOOLEAN      DEFAULT FALSE,
    lease_id        VARCHAR(255)
        CONSTRAINT policy_monitor_lease_lease_id_fk
            REFERENCES edc_lease ON DELETE SET NULL
);
