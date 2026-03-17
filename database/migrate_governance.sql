-- Migration optionnelle (base Postgres déjà créée sans governance_access)
-- psql -U ude_admin -d urban_data -h localhost -p 5433 -f database/migrate_governance.sql

CREATE TABLE IF NOT EXISTS governance_access (
    role_name VARCHAR(32) PRIMARY KEY,
    profil VARCHAR(64) NOT NULL,
    description TEXT NOT NULL,
    select_allowed BOOLEAN NOT NULL DEFAULT FALSE,
    write_allowed BOOLEAN NOT NULL DEFAULT FALSE
);

INSERT INTO governance_access (role_name, profil, description, select_allowed, write_allowed) VALUES
    ('ude_admin', 'Équipe data / pipeline', 'Chargement Gold, tables métier, audit pipeline_runs', TRUE, TRUE),
    ('ude_reader', 'Client / API / BI', 'Lecture universelle : vues métier et tables de référence', TRUE, FALSE)
ON CONFLICT (role_name) DO NOTHING;

CREATE OR REPLACE VIEW v_catalogue_donnees AS
SELECT 'arrondissements' AS objet, 'table' AS type, 'Référentiel géographique Paris 1-20' AS description
UNION ALL SELECT 'prix_annuel', 'table', 'Série temporelle prix m² et transactions'
UNION ALL SELECT 'indicateurs_arrondissement', 'table', 'Indicateurs socio-éco, typologie JSON'
UNION ALL SELECT 'v_prix_par_annee', 'vue', 'Prix par arrondissement et année (accès client)'
UNION ALL SELECT 'v_indicateurs_complets', 'vue', 'Indicateurs fusionnés pour cartographie'
UNION ALL SELECT 'v_accessibilite_prix_revenu', 'vue', 'Ratio accessibilité logement (besoin client)'
UNION ALL SELECT 'v_catalogue_donnees', 'vue', 'Catalogue des objets accessibles en lecture'
UNION ALL SELECT 'integration_report', 'table', 'Traçabilité sources open data'
UNION ALL SELECT 'governance_access', 'table', 'Matrice des rôles et droits';

GRANT SELECT ON governance_access TO ude_reader;
GRANT SELECT ON v_catalogue_donnees TO ude_reader;
