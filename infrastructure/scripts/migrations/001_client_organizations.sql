CREATE SCHEMA IF NOT EXISTS identity;

CREATE TABLE IF NOT EXISTS identity.client_organizations (
    id                       VARCHAR(36) PRIMARY KEY,
    identifier               VARCHAR(64) NOT NULL UNIQUE,
    name                     VARCHAR(128) NOT NULL,
    description              TEXT NOT NULL DEFAULT '',
    client_type              VARCHAR(32) NOT NULL,
    deployment_model         VARCHAR(32) NOT NULL,
    status                   VARCHAR(64) NOT NULL DEFAULT 'draft',
    status_options           JSONB NOT NULL DEFAULT '["draft","active","inactive","suspended","archived"]'::jsonb,
    primary_contact_name     VARCHAR(128) NOT NULL,
    primary_contact_email    VARCHAR(254) NOT NULL,
    superadmin_name          VARCHAR(128) NOT NULL,
    superadmin_email         VARCHAR(254) NOT NULL,
    access_setup_status      VARCHAR(32) NOT NULL DEFAULT 'pending_client_workspace',
    created_at               TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at               TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_client_organizations_status
    ON identity.client_organizations(status);
