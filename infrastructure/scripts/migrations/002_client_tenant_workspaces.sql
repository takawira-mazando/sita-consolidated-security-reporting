CREATE SCHEMA IF NOT EXISTS identity;

CREATE TABLE IF NOT EXISTS identity.client_tenant_workspaces (
    id                       VARCHAR(36) PRIMARY KEY,
    client_organization_id   VARCHAR(36) NOT NULL
        REFERENCES identity.client_organizations(id) ON DELETE CASCADE,
    identifier               VARCHAR(64) NOT NULL,
    name                     VARCHAR(128) NOT NULL,
    status                   VARCHAR(32) NOT NULL DEFAULT 'active',
    root_label               VARCHAR(64) NOT NULL DEFAULT 'Organization',
    administration_model     VARCHAR(24) NOT NULL DEFAULT 'mssp_managed',
    hierarchy_levels         JSONB NOT NULL DEFAULT '[]'::jsonb,
    org_units                JSONB NOT NULL DEFAULT '[]'::jsonb,
    roles                    JSONB NOT NULL DEFAULT '[]'::jsonb,
    assignments              JSONB NOT NULL DEFAULT '[]'::jsonb,
    created_at               TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at               TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_client_tenant_workspace_identifier
        UNIQUE (client_organization_id, identifier)
);

CREATE INDEX IF NOT EXISTS idx_client_tenant_workspaces_client
    ON identity.client_tenant_workspaces(client_organization_id);
