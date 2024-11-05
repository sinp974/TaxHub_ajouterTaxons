-- Supprimer la table taxonomie.vm_taxref_hierarchie existante
DROP TABLE IF EXISTS taxonomie.vm_taxref_hierarchie;

-- Recréer la table avec les colonnes adaptées
CREATE TABLE taxonomie.vm_taxref_hierarchie (
    regne VARCHAR(20) DEFAULT 'pg_catalog.default',
    phylum VARCHAR(50) DEFAULT 'pg_catalog.default',
    classe VARCHAR(50) DEFAULT 'pg_catalog.default',
    ordre VARCHAR(50) DEFAULT 'pg_catalog.default',
    famille VARCHAR(50) DEFAULT 'pg_catalog.default',
    sous_famille VARCHAR(50) DEFAULT 'pg_catalog.default',
    tribu VARCHAR(50) DEFAULT 'pg_catalog.default',
    cd_nom INTEGER,
    cd_ref INTEGER,
    lb_nom VARCHAR(250) DEFAULT 'pg_catalog.default',
    id_rang VARCHAR(10) DEFAULT 'pg_catalog.default',
    nb_tx_tr BIGINT,
    nb_tx_sbfm BIGINT,
    nb_tx_fm BIGINT,
    nb_tx_or BIGINT,
    nb_tx_cl BIGINT,
    nb_tx_ph BIGINT,
    nb_tx_kd BIGINT
);

-- Insérer les données dans la table
INSERT INTO taxonomie.vm_taxref_hierarchie
SELECT tx.regne, tx.phylum, tx.classe, tx.ordre, tx.famille, tx.sous_famille, tx.tribu, tx.cd_nom, tx.cd_ref, lb_nom, trim(id_rang)
	AS id_rang, t.nb_tx_tr, s.nb_tx_sbfm, f.nb_tx_fm, o.nb_tx_or, c.nb_tx_cl, p.nb_tx_ph, r.nb_tx_kd
	FROM taxonomie.taxref tx
  LEFT JOIN (SELECT tribu ,count(*) AS nb_tx_tr  FROM taxonomie.taxref where id_rang NOT IN ('TR') GROUP BY  tribu) t ON t.tribu = tx.tribu
  LEFT JOIN (SELECT sous_famille ,count(*) AS nb_tx_sbfm  FROM taxonomie.taxref where id_rang NOT IN ('SBFM') GROUP BY  sous_famille) s ON s.sous_famille = tx.sous_famille
  LEFT JOIN (SELECT famille ,count(*) AS nb_tx_fm  FROM taxonomie.taxref where id_rang NOT IN ('FM') GROUP BY  famille) f ON f.famille = tx.famille
  LEFT JOIN (SELECT ordre ,count(*) AS nb_tx_or FROM taxonomie.taxref where id_rang NOT IN ('OR') GROUP BY  ordre) o ON o.ordre = tx.ordre
  LEFT JOIN (SELECT classe ,count(*) AS nb_tx_cl  FROM taxonomie.taxref where id_rang NOT IN ('CL') GROUP BY  classe) c ON c.classe = tx.classe
  LEFT JOIN (SELECT phylum ,count(*) AS nb_tx_ph  FROM taxonomie.taxref where id_rang NOT IN ('PH') GROUP BY  phylum) p ON p.phylum = tx.phylum
  LEFT JOIN (SELECT regne ,count(*) AS nb_tx_kd  FROM taxonomie.taxref where id_rang NOT IN ('KD') GROUP BY  regne) r ON r.regne = tx.regne
WHERE id_rang IN ('KD','PH','CL','OR','FM', 'SBFM', 'TR') AND tx.cd_nom = tx.cd_ref;

REFRESH MATERIALIZED VIEW taxonomie.vm_taxref_list_forautocomplete;
REFRESH MATERIALIZED VIEW taxonomie.vm_classe;
REFRESH MATERIALIZED VIEW taxonomie.vm_famille;
REFRESH MATERIALIZED VIEW taxonomie.vm_group1_inpn;
REFRESH MATERIALIZED VIEW taxonomie.vm_group2_inpn;
REFRESH MATERIALIZED VIEW taxonomie.vm_ordre;
REFRESH MATERIALIZED VIEW taxonomie.vm_phylum;
REFRESH MATERIALIZED VIEW taxonomie.vm_regne;
