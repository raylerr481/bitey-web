-- Pin the function search_path to avoid mutable search_path execution risk.
alter function bitey.match_memories(vector, integer)
set search_path = pg_catalog, bitey, public;
