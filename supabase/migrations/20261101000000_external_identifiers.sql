-- BRVM-AI — registre explicite des identifiants multi-sources.
-- Une correspondance externe ne doit jamais être déduite d'une ressemblance de noms.

CREATE TABLE brvm.security_external_identifier (
    security_external_identifier_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    security_id uuid NOT NULL,
    source_id uuid NOT NULL REFERENCES brvm.data_source (source_id)
        ON UPDATE RESTRICT ON DELETE RESTRICT,
    identifier_type text NOT NULL CHECK (length(btrim(identifier_type)) > 0),
    identifier text NOT NULL CHECK (length(btrim(identifier)) > 0),
    verification_status text NOT NULL DEFAULT 'pending'
        CHECK (verification_status IN ('pending', 'verified', 'rejected')),
    source_document_id uuid REFERENCES brvm.source_document (source_document_id)
        ON UPDATE RESTRICT ON DELETE RESTRICT,
    valid_from date,
    valid_to date,
    notes text,
    created_at timestamptz NOT NULL DEFAULT transaction_timestamp(),
    updated_at timestamptz NOT NULL DEFAULT transaction_timestamp(),
    CONSTRAINT security_external_identifier_security_fk
        FOREIGN KEY (security_id) REFERENCES brvm.security (security_id)
        ON UPDATE RESTRICT ON DELETE RESTRICT,
    CONSTRAINT security_external_identifier_valid_range
        CHECK (valid_to IS NULL OR valid_from IS NULL OR valid_to >= valid_from),
    CONSTRAINT security_external_identifier_value_normalized
        CHECK (identifier = btrim(identifier))
);

CREATE UNIQUE INDEX security_external_identifier_active_unique
    ON brvm.security_external_identifier (source_id, identifier_type, identifier)
    WHERE valid_to IS NULL AND verification_status <> 'rejected';

CREATE INDEX security_external_identifier_lookup_idx
    ON brvm.security_external_identifier
       (source_id, identifier_type, identifier, verification_status, valid_from, valid_to);

CREATE INDEX security_external_identifier_security_idx
    ON brvm.security_external_identifier (security_id, source_id);

CREATE TRIGGER security_external_identifier_touch_updated_at
BEFORE UPDATE ON brvm.security_external_identifier
FOR EACH ROW EXECUTE FUNCTION brvm.touch_updated_at();

COMMENT ON TABLE brvm.security_external_identifier IS
    'Correspondances explicites entre un titre BRVM et les identifiants des fournisseurs externes.';
COMMENT ON COLUMN brvm.security_external_identifier.verification_status IS
    'pending = à vérifier, verified = utilisable pour la consolidation, rejected = interdit.';
COMMENT ON COLUMN brvm.security_external_identifier.source_document_id IS
    'Document ou référence justifiant la correspondance lorsqu’il est disponible.';
