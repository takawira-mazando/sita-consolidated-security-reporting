CREATE SCHEMA IF NOT EXISTS identity;

CREATE TABLE IF NOT EXISTS identity.client_superadmin_invitations (
    id                       VARCHAR(36) PRIMARY KEY,
    client_organization_id   VARCHAR(36) NOT NULL
        REFERENCES identity.client_organizations(id) ON DELETE CASCADE,
    person_id                VARCHAR(36) NOT NULL
        REFERENCES identity.persons(id) ON DELETE RESTRICT,
    email                    VARCHAR(255) NOT NULL,
    token_hash               VARCHAR(64) NOT NULL UNIQUE,
    expires_at               TIMESTAMPTZ NOT NULL,
    used_at                  TIMESTAMPTZ,
    revoked_at               TIMESTAMPTZ,
    created_by               VARCHAR(255) NOT NULL,
    created_at               TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_client_superadmin_invitations_client
    ON identity.client_superadmin_invitations(client_organization_id);
CREATE INDEX IF NOT EXISTS idx_client_superadmin_invitations_person
    ON identity.client_superadmin_invitations(person_id);
