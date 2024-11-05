--#######################################################################
--  OPTIMISATION rafraichissement de la vue taxref for autocomplete
--#######################################################################

DROP MATERIALIZED VIEW taxonomie.vm_taxref_list_forautocomplete;
CREATE TABLE taxonomie.vm_taxref_list_forautocomplete AS
SELECT t.cd_nom,
  t.search_name,
  t.nom_valide,
  t.lb_nom,
  t.regne,
  t.group2_inpn,
  l.id_liste
 FROM ( SELECT t_1.cd_nom,
          concat(t_1.lb_nom, ' = ', t_1.nom_complet_html) AS search_name,
          t_1.nom_valide,
          t_1.lb_nom,
          t_1.regne,
          t_1.group2_inpn
         FROM taxonomie.taxref t_1
      UNION
       SELECT t_1.cd_nom,
          concat(n.nom_francais, ' = ', t_1.nom_complet_html) AS search_name,
          t_1.nom_valide,
          t_1.lb_nom,
          t_1.regne,
          t_1.group2_inpn
         FROM taxonomie.taxref t_1
         JOIN taxonomie.bib_noms n
         ON t_1.cd_nom = n.cd_nom
        WHERE t_1.nom_vern IS NOT NULL) t
   JOIN taxonomie.v_taxref_all_listes l ON t.cd_nom = l.cd_nom;
COMMENT ON TABLE taxonomie.vm_taxref_list_forautocomplete
     IS 'Table construite à partir d''une requete sur la base et mise à jour via le trigger trg_refresh_mv_taxref_list_forautocomplete de la table cor_nom_liste';


CREATE INDEX i_vm_taxref_list_forautocomplete_cd_nom
  ON taxonomie.vm_taxref_list_forautocomplete (cd_nom ASC NULLS LAST);
CREATE INDEX i_vm_taxref_list_forautocomplete_search_name
  ON taxonomie.vm_taxref_list_forautocomplete (search_name ASC NULLS LAST);


CREATE OR REPLACE FUNCTION taxonomie.trg_fct_refresh_mv_taxref_list_forautocomplete()
  RETURNS trigger AS
$BODY$
DECLARE
	new_cd_nom int;
	new_nom_vern varchar(500);
BEGIN
	IF TG_OP in ('DELETE', 'TRUNCATE', 'UPDATE') THEN
	    DELETE FROM taxonomie.vm_taxref_list_forautocomplete WHERE cd_nom IN (
		SELECT cd_nom FROM taxonomie.bib_noms WHERE id_nom =  OLD.id_nom
	    );
	END IF;
	IF TG_OP in ('INSERT', 'UPDATE') THEN
		SELECT cd_nom, nom_francais INTO new_cd_nom, new_nom_vern FROM taxonomie.bib_noms WHERE id_nom = NEW.id_nom;

		INSERT INTO taxonomie.vm_taxref_list_forautocomplete
		SELECT t.cd_nom,
		    concat(t.lb_nom, ' = ', t.nom_complet_html) AS search_name,
		    t.nom_valide,
		    t.lb_nom,
		    t.regne,
		    t.group2_inpn,
		    NEW.id_liste
		FROM taxonomie.taxref t  WHERE cd_nom = new_cd_nom;


		IF NOT new_nom_vern IS NULL THEN
			INSERT INTO taxonomie.vm_taxref_list_forautocomplete
			SELECT t.cd_nom,
			    concat(new_nom_vern, ' = ', t.nom_complet_html) AS search_name,
			    t.nom_valide,
			    t.lb_nom,
			    t.regne,
			    t.group2_inpn,
  		    NEW.id_liste
			FROM taxonomie.taxref t
			WHERE cd_nom = new_cd_nom;
		END IF;
	END IF;
  RETURN NEW;
END;
$BODY$
  LANGUAGE plpgsql VOLATILE
  COST 100;



CREATE TRIGGER trg_refresh_mv_taxref_list_forautocomplete
  AFTER INSERT OR UPDATE OR DELETE
  ON taxonomie.cor_nom_liste
  FOR EACH ROW
  EXECUTE PROCEDURE taxonomie.trg_fct_refresh_mv_taxref_list_forautocomplete();



CREATE OR REPLACE FUNCTION taxonomie.trg_fct_refresh_nomfrancais_mv_taxref_list_forautocomplete()
  RETURNS trigger AS
$BODY$
DECLARE
BEGIN
    UPDATE taxonomie.vm_taxref_list_forautocomplete v SET search_name = concat(NEW.nom_francais, ' = ', t.nom_complet_html)
    FROM taxonomie.taxref t
		WHERE v.cd_nom = NEW.cd_nom AND t.cd_nom = NEW.cd_nom;
    RETURN NEW;
END;
$BODY$
  LANGUAGE plpgsql VOLATILE
  COST 100;

CREATE TRIGGER trg_refresh_nomfrancais_mv_taxref_list_forautocomplete AFTER UPDATE OF nom_francais
ON taxonomie.bib_noms FOR EACH ROW
EXECUTE PROCEDURE taxonomie.trg_fct_refresh_nomfrancais_mv_taxref_list_forautocomplete();
