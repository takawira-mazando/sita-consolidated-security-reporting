BEGIN;

DROP SCHEMA IF EXISTS hr CASCADE;

DO $ldap_only$
BEGIN
    IF to_regclass('identity.persons') IS NOT NULL THEN
        IF to_regclass('identity.client_superadmin_invitations') IS NOT NULL THEN
            DELETE FROM identity.client_superadmin_invitations invitation
            USING identity.persons person
            WHERE invitation.person_id = person.id
              AND COALESCE(person.source, '') NOT IN ('ldap', 'active_directory', 'directory');
        END IF;

        IF to_regclass('identity.users') IS NOT NULL THEN
            DELETE FROM identity.users account
            USING identity.persons person
            WHERE account.person_id = person.id
              AND COALESCE(person.source, '') NOT IN ('ldap', 'active_directory', 'directory');
        END IF;

        DELETE FROM identity.persons
        WHERE COALESCE(source, '') NOT IN ('ldap', 'active_directory', 'directory');

        ALTER TABLE identity.persons
            DROP CONSTRAINT IF EXISTS ck_persons_ldap_source;
        ALTER TABLE identity.persons
            ADD CONSTRAINT ck_persons_ldap_source
            CHECK (source IN ('ldap', 'active_directory', 'directory'));
    END IF;

    IF to_regclass('identity.employment_identifier') IS NOT NULL THEN
        DELETE FROM identity.employment_identifier
        WHERE COALESCE(scheme, '') <> 'ldap';

        ALTER TABLE identity.employment_identifier
            DROP CONSTRAINT IF EXISTS ck_employment_identifier_ldap_only;
        ALTER TABLE identity.employment_identifier
            ADD CONSTRAINT ck_employment_identifier_ldap_only
            CHECK (scheme = 'ldap');
    END IF;
END
$ldap_only$;

COMMIT;
