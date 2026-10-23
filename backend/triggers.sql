-- Appliqué par `flask init-db` (PostgreSQL uniquement). Idempotent.
CREATE EXTENSION IF NOT EXISTS pg_trgm;

CREATE OR REPLACE FUNCTION forbid_mutation() RETURNS trigger AS $$
BEGIN
  RAISE EXCEPTION 'Table en lecture seule (traçabilité) : % interdit sur %', TG_OP, TG_TABLE_NAME;
END $$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS no_mutation ON stock_movements;
CREATE TRIGGER no_mutation BEFORE UPDATE OR DELETE ON stock_movements FOR EACH ROW EXECUTE FUNCTION forbid_mutation();
DROP TRIGGER IF EXISTS no_mutation ON audit_logs;
CREATE TRIGGER no_mutation BEFORE UPDATE OR DELETE ON audit_logs FOR EACH ROW EXECUTE FUNCTION forbid_mutation();
DROP TRIGGER IF EXISTS no_mutation ON credit_notes;
CREATE TRIGGER no_mutation BEFORE UPDATE OR DELETE ON credit_notes FOR EACH ROW EXECUTE FUNCTION forbid_mutation();
DROP TRIGGER IF EXISTS no_mutation ON inventory_items;
CREATE TRIGGER no_mutation BEFORE UPDATE OR DELETE ON inventory_items FOR EACH ROW EXECUTE FUNCTION forbid_mutation();

-- Une facture ne peut jamais être supprimée (seul le statut peut passer à ANNULEE)
DROP TRIGGER IF EXISTS no_delete ON invoices;
CREATE TRIGGER no_delete BEFORE DELETE ON invoices FOR EACH ROW EXECUTE FUNCTION forbid_mutation();
DROP TRIGGER IF EXISTS no_delete ON sales;
CREATE TRIGGER no_delete BEFORE DELETE ON sales FOR EACH ROW EXECUTE FUNCTION forbid_mutation();
DROP TRIGGER IF EXISTS no_delete ON sale_items;
CREATE TRIGGER no_delete BEFORE DELETE ON sale_items FOR EACH ROW EXECUTE FUNCTION forbid_mutation();

-- Recherche rapide (texte partiel) sur de gros volumes
CREATE INDEX IF NOT EXISTS ix_products_name_trgm ON products USING gin (name gin_trgm_ops);
CREATE INDEX IF NOT EXISTS ix_products_ref_trgm ON products USING gin (reference gin_trgm_ops);
CREATE INDEX IF NOT EXISTS ix_customers_name_trgm ON customers USING gin (name gin_trgm_ops);
CREATE INDEX IF NOT EXISTS ix_customers_phone_trgm ON customers USING gin (phone gin_trgm_ops);
CREATE INDEX IF NOT EXISTS ix_invoices_number_trgm ON invoices USING gin (number gin_trgm_ops);
