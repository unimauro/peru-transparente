// Perú Transparente — bootstrap del grafo de poder (Neo4j)
// Constraints
CREATE CONSTRAINT person_id   IF NOT EXISTS FOR (p:Person)   REQUIRE p.id IS UNIQUE;
CREATE CONSTRAINT entity_id   IF NOT EXISTS FOR (e:Entity)   REQUIRE e.id IS UNIQUE;
CREATE CONSTRAINT sector_id   IF NOT EXISTS FOR (s:Sector)   REQUIRE s.id IS UNIQUE;
CREATE CONSTRAINT position_id IF NOT EXISTS FOR (x:Position) REQUIRE x.id IS UNIQUE;
CREATE CONSTRAINT company_id  IF NOT EXISTS FOR (c:Company)  REQUIRE c.id IS UNIQUE;
CREATE CONSTRAINT supplier_id IF NOT EXISTS FOR (s:Supplier) REQUIRE s.id IS UNIQUE;
CREATE CONSTRAINT contract_id IF NOT EXISTS FOR (k:Contract) REQUIRE k.id IS UNIQUE;
CREATE CONSTRAINT decl_id     IF NOT EXISTS FOR (d:Declaration) REQUIRE d.id IS UNIQUE;
CREATE CONSTRAINT res_id      IF NOT EXISTS FOR (r:Resolution)  REQUIRE r.id IS UNIQUE;

// Índices
CREATE INDEX person_name  IF NOT EXISTS FOR (p:Person)   ON (p.normalizedName);
CREATE INDEX entity_ruc   IF NOT EXISTS FOR (e:Entity)   ON (e.ruc);
CREATE INDEX supplier_ruc IF NOT EXISTS FOR (s:Supplier) ON (s.ruc);
CREATE INDEX entity_name  IF NOT EXISTS FOR (e:Entity)   ON (e.name);
