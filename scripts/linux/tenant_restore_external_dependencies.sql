-- Used against the isolated full restore BEFORE replacing the tenant schema.
-- DROP SCHEMA CASCADE would also remove these objects/constraints in neighbors.
SELECT
  (SELECT count(*)
   FROM pg_constraint c
   JOIN pg_class source ON source.oid = c.conrelid
   JOIN pg_namespace source_ns ON source_ns.oid = source.relnamespace
   JOIN pg_class target ON target.oid = c.confrelid
   JOIN pg_namespace target_ns ON target_ns.oid = target.relnamespace
   WHERE c.contype = 'f'
     AND target_ns.nspname = :'tenant_schema'
     AND source_ns.nspname <> target_ns.nspname)
  +
  (SELECT count(DISTINCT view_relation.oid)
   FROM pg_depend d
   JOIN pg_rewrite r ON d.classid = 'pg_rewrite'::regclass AND d.objid = r.oid
   JOIN pg_class view_relation ON view_relation.oid = r.ev_class
   JOIN pg_namespace view_ns ON view_ns.oid = view_relation.relnamespace
   JOIN pg_class target ON d.refclassid = 'pg_class'::regclass AND d.refobjid = target.oid
   JOIN pg_namespace target_ns ON target_ns.oid = target.relnamespace
   WHERE target_ns.nspname = :'tenant_schema'
     AND view_ns.nspname <> target_ns.nspname);
