-- Urban Data Explorer — BDD relationnelle (compétence RNCP)
-- Gouvernance : ude_admin (écriture pipeline) | ude_reader (lecture client universelle)

CREATE USER ude_reader WITH PASSWORD 'ude_reader_dev';

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

CREATE TABLE IF NOT EXISTS pipeline_runs (
    id SERIAL PRIMARY KEY,
    started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    finished_at TIMESTAMPTZ,
    status VARCHAR(32),
    metrics_json JSONB
);

CREATE TABLE IF NOT EXISTS arrondissements (
    arrondissement INTEGER PRIMARY KEY CHECK (arrondissement BETWEEN 1 AND 20),
    nom VARCHAR(64) NOT NULL,
    code_insee CHAR(5) NOT NULL UNIQUE,
    longitude DOUBLE PRECISION,
    latitude DOUBLE PRECISION,
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS prix_annuel (
    id SERIAL PRIMARY KEY,
    arrondissement INTEGER NOT NULL REFERENCES arrondissements(arrondissement) ON DELETE CASCADE,
    annee INTEGER NOT NULL CHECK (annee >= 2018 AND annee <= 2030),
    prix_m2_median DOUBLE PRECISION,
    nombre_transactions INTEGER,
    variation_annuelle_pct DOUBLE PRECISION,
    UNIQUE (arrondissement, annee)
);

CREATE TABLE IF NOT EXISTS indicateurs_arrondissement (
    arrondissement INTEGER PRIMARY KEY REFERENCES arrondissements(arrondissement) ON DELETE CASCADE,
    logements_sociaux_pct DOUBLE PRECISION,
    revenu_median_menage INTEGER,
    revenu_moyen_menage INTEGER,
    densite_km2 INTEGER,
    population INTEGER,
    pollution_indice_atmo DOUBLE PRECISION,
    delits_par_1000 DOUBLE PRECISION,
    total_delits INTEGER,
    typologie_json JSONB,
    sources_json JSONB,
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS integration_report (
    id SERIAL PRIMARY KEY,
    report_json JSONB NOT NULL,
    sources_updated_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE OR REPLACE VIEW v_prix_par_annee AS
SELECT a.arrondissement, a.nom, a.code_insee, p.annee,
       p.prix_m2_median, p.variation_annuelle_pct, p.nombre_transactions
FROM arrondissements a
JOIN prix_annuel p ON p.arrondissement = a.arrondissement
ORDER BY a.arrondissement, p.annee;

CREATE OR REPLACE VIEW v_indicateurs_complets AS
SELECT a.arrondissement, a.nom, a.code_insee,
       i.logements_sociaux_pct, i.revenu_median_menage, i.densite_km2,
       i.pollution_indice_atmo, i.delits_par_1000, i.typologie_json
FROM arrondissements a
LEFT JOIN indicateurs_arrondissement i ON i.arrondissement = a.arrondissement;

CREATE OR REPLACE VIEW v_accessibilite_prix_revenu AS
SELECT a.arrondissement, a.nom,
       p.prix_m2_median,
       i.revenu_median_menage,
       CASE WHEN i.revenu_median_menage > 0 AND p.prix_m2_median > 0
            THEN ROUND(((p.prix_m2_median * 50.0) / (i.revenu_median_menage / 12.0))::numeric, 2)
            ELSE NULL END AS mois_revenu_pour_50m2
FROM arrondissements a
JOIN indicateurs_arrondissement i ON i.arrondissement = a.arrondissement
JOIN prix_annuel p ON p.arrondissement = a.arrondissement
WHERE p.annee = (SELECT MAX(annee) FROM prix_annuel);

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

COMMENT ON TABLE arrondissements IS 'Référentiel — accès lecture via ude_reader';
COMMENT ON VIEW v_accessibilite_prix_revenu IS 'Besoin client : mois de revenu pour 50 m²';

-- Gouvernance : lecture seule universelle pour le client
GRANT CONNECT ON DATABASE urban_data TO ude_reader;
GRANT USAGE ON SCHEMA public TO ude_reader;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO ude_reader;
GRANT SELECT ON ALL SEQUENCES IN SCHEMA public TO ude_reader;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO ude_reader;
-- Pas d''écriture pour ude_reader (pipeline = ude_admin uniquement)
REVOKE INSERT, UPDATE, DELETE, TRUNCATE ON ALL TABLES IN SCHEMA public FROM ude_reader;
