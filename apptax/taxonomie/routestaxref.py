from warnings import warn

from flask import abort, jsonify, Blueprint, request
from sqlalchemy import distinct, desc, func, and_
from sqlalchemy.orm.exc import NoResultFound
from sqlalchemy.orm import raiseload, joinedload, aliased

from ..utils.utilssqlalchemy import json_resp, serializeQuery, serializeQueryOneResult
from .models import (
    Taxref,
    BibNoms,
    VMTaxrefListForautocomplete,
    BibTaxrefHabitats,
    BibTaxrefRangs,
    BibTaxrefStatus,
    VMTaxrefHierarchie,
    VTaxrefHierarchieBibtaxons,
    CorNomListe,
    BibListes,
    TMetaTaxref,
)

from .repositories import BdcStatusRepository

try:
    from urllib.parse import unquote
except ImportError:
    from urllib import unquote

from . import db

adresses = Blueprint("taxref", __name__)


@adresses.route("/", methods=["GET"])
@json_resp
def getTaxrefList():
    return genericTaxrefList(False, request.args)


@adresses.route("/version", methods=["GET"])
@json_resp
def getTaxrefVersion():
    """
    La table TMetaTaxref contient la liste des référentiels contenu dans la table taxref
    Cette route renvoie le dernier référentiel qui a été MAJ
    (utilisé pour le mobile pour retélécharger le référentiel lorsque celui ci à changé ou en MAJ)
    """
    taxref_version = TMetaTaxref.query.order_by(TMetaTaxref.update_date.desc()).first()
    if not taxref_version:
        return {"msg": "Table t_meta_taxref non peuplée"}, 500
    return taxref_version.as_dict()


@adresses.route("/bibnoms/", methods=["GET"])
@json_resp
def getTaxrefBibtaxonList():
    return genericTaxrefList(True, request.args)


@adresses.route("/search/<field>/<ilike>", methods=["GET"])
def getSearchInField(field, ilike):
    """.. http:get:: /taxref/search/(str:field)/(str:ilike)
    .. :quickref: Taxref;

    Retourne les 20 premiers résultats de la table "taxref" pour une
    requête sur le champ `field` avec ILIKE et la valeur `ilike` fournie.
    L'algorithme Trigramme est utilisé pour établir la correspondance.

    :query fields: Permet de récupérer des champs suplémentaires de la
        table "taxref" dans la réponse. Séparer les noms des champs par
        des virgules.
    :query is_inbibnom: Ajoute une jointure sur la table "bib_noms".
    :query add_rank: Ajoute une jointure sur la table "bib_taxref_rangs"
        et la colonne nom_rang aux résultats.
    :query rank_limit: Retourne seulement les taxons dont le rang est
        supérieur ou égal au rang donné. Le rang passé doit être une
        valeur de la colonne "id_rang" de la table "bib_taxref_rangs".

    :statuscode 200: Tableau de dictionnaires correspondant aux résultats
        de la recherche dans la table "taxref".
    :statuscode 500: Aucun rang ne correspond à la valeur fournie.
                     Aucune colonne ne correspond à la valeur fournie.
    """
    taxrefColumns = Taxref.__table__.columns
    if field in taxrefColumns:
        value = unquote(ilike)
        value = value.replace(" ", "%")
        column = taxrefColumns[field]
        q = (
            db.session.query(
                column,
                Taxref.cd_nom,
                Taxref.cd_ref,
                func.similarity(column, value).label("idx_trgm"),
            )
            .filter(column.ilike("%" + value + "%"))
            .order_by(desc("idx_trgm"))
        )

        if request.args.get("fields"):
            fields = request.args["fields"].split(",")
            for field in fields:
                if field in taxrefColumns:
                    column = taxrefColumns[field]
                    q = q.add_columns(column)
                else:
                    msg = f"No column found in Taxref for {field}"
                    return jsonify(msg), 500

        if request.args.get("is_inbibnoms"):
            q = q.join(BibNoms, BibNoms.cd_nom == Taxref.cd_nom)
        join_on_bib_rang = False
        if request.args.get("add_rank"):
            q = q.join(BibTaxrefRangs, Taxref.id_rang == BibTaxrefRangs.id_rang)
            q = q.add_columns(BibTaxrefRangs.nom_rang)
            join_on_bib_rang = True

        if "rank_limit" in request.args:
            if not join_on_bib_rang:
                q = q.join(BibTaxrefRangs, Taxref.id_rang == BibTaxrefRangs.id_rang)
            try:
                sub_q_id_rang = (
                    db.session.query(BibTaxrefRangs.tri_rang)
                    .filter(BibTaxrefRangs.id_rang == request.args["rank_limit"])
                    .one()
                )
            except NoResultFound:
                return (
                    jsonify("No rank found for {}".format(request.args["rank_limit"])),
                    500,
                )
            q = q.filter(BibTaxrefRangs.tri_rang <= sub_q_id_rang[0])

        results = q.limit(20).all()
        return jsonify(serializeQuery(results, q.column_descriptions))
    else:
        jsonify("No column found in Taxref for {}".format(field)), 500


@adresses.route("/<int(signed=True):id>", methods=["GET"])
def getTaxrefDetail(id):
    dfCdNom = Taxref.__table__.columns["cd_nom"]

    q = (
        db.session.query(
            Taxref.cd_nom,
            Taxref.cd_ref,
            Taxref.regne,
            Taxref.phylum,
            Taxref.classe,
            Taxref.ordre,
            Taxref.famille,
            Taxref.cd_taxsup,
            Taxref.cd_sup,
            Taxref.cd_taxsup,
            Taxref.nom_complet,
            Taxref.nom_valide,
            Taxref.nom_vern,
            Taxref.group1_inpn,
            Taxref.group2_inpn,
            Taxref.group3_inpn,
            Taxref.id_rang,
            BibTaxrefRangs.nom_rang,
            BibTaxrefStatus.nom_statut,
            BibTaxrefHabitats.nom_habitat,
        )
        .outerjoin(BibTaxrefHabitats, BibTaxrefHabitats.id_habitat == Taxref.id_habitat)
        .outerjoin(BibTaxrefStatus, BibTaxrefStatus.id_statut == Taxref.id_statut)
        .outerjoin(BibTaxrefRangs, BibTaxrefRangs.id_rang == Taxref.id_rang)
        .filter(dfCdNom == id)
    )

    results = q.one()

    taxon = serializeQueryOneResult(results, q.column_descriptions)

    qsynonymes = db.session.query(Taxref.cd_nom, Taxref.nom_complet).filter(
        Taxref.cd_ref == results.cd_ref
    )

    synonymes = qsynonymes.all()

    taxon["synonymes"] = [
        {c: getattr(row, c) for c in ["cd_nom", "nom_complet"] if getattr(row, c) is not None}
        for row in synonymes
    ]

    areas = None
    if request.args.get("areas_status"):
        areas = request.args["areas_status"].split(",")

    areas_code = None
    if request.args.get("areas_code_status"):
        areas_code = request.args["areas_code_status"].split(",")

    taxon["status"] = BdcStatusRepository().get_status(
        cd_ref=results.cd_ref, areas=areas, areas_code=areas_code, type_statut=None, format=True
    )

    return jsonify(taxon)


@adresses.route("/distinct/<field>", methods=["GET"])
def getDistinctField(field):
    taxrefColumns = Taxref.__table__.columns
    q = db.session.query(taxrefColumns[field]).distinct(taxrefColumns[field])

    limit = request.args.get("limit", 100, int)

    for param in request.args:
        if param in taxrefColumns:
            col = getattr(taxrefColumns, param)
            q = q.filter(col == request.args[param])
        elif param == "ilike":
            q = q.filter(taxrefColumns[field].ilike(request.args[param] + "%"))

    results = q.limit(limit).all()
    return jsonify(serializeQuery(results, q.column_descriptions))


@adresses.route("/hierarchie/<rang>", methods=["GET"])
@json_resp
def getTaxrefHierarchie(rang):
    results = genericHierarchieSelect(VMTaxrefHierarchie, rang, request.args)
    return [r.as_dict() for r in results]


@adresses.route("/hierarchiebibtaxons/<rang>", methods=["GET"])
@json_resp
def getTaxrefHierarchieBibNoms(rang):
    results = genericHierarchieSelect(VTaxrefHierarchieBibtaxons, rang, request.args)
    return [r.as_dict() for r in results]


@adresses.route("/regnewithgroupe2", methods=["GET"])
@json_resp
def get_regneGroup2Inpn_taxref():
    """
    Retourne la liste des règnes et groupes 2
        définis par Taxref de façon hiérarchique
    formatage : {'regne1':['grp1', 'grp2'], 'regne2':['grp3', 'grp4']}
    """
    q = (
        db.session.query(Taxref.regne, Taxref.group2_inpn)
        .distinct(Taxref.regne, Taxref.group2_inpn)
        .filter(Taxref.regne != None)
        .filter(Taxref.group2_inpn != None)
    )
    data = q.all()
    results = {"": [""]}
    for d in data:
        if d.regne in results:
            results[d.regne].append(d.group2_inpn)
        else:
            results[d.regne] = ["", d.group2_inpn]
    return results


@adresses.route("/idNomStatuts", methods=["GET"])
@json_resp
def get_id_nom_statuts():
    """
    Retourne un dictionnaire contenant la liste des id des statuts et leur nom associé,
    trié par ordre alphabétique sur les noms.
    """
    subquery = (
        db.session.query(BibTaxrefStatus.id_statut, BibTaxrefStatus.nom_statut).distinct(
            BibTaxrefStatus.id_statut
        )
    ).subquery()

    data = db.session.query(subquery).order_by(subquery.c.nom_statut.asc()).all()

    return [{"id_statut": id_statut, "nom_statut": nom_statut} for id_statut, nom_statut in data]


@adresses.route("/idNomHabitats", methods=["GET"])
@json_resp
def get_id_nom_habitats():
    """
    Retourne un dictionnaire contenant la liste des id des habitats et leur nom associé,
    trié par ordre alphabétique sur les noms.
    """
    subquery = (
        db.session.query(BibTaxrefHabitats.id_habitat, BibTaxrefHabitats.nom_habitat).distinct(
            BibTaxrefHabitats.id_habitat
        )
    ).subquery()

    data = db.session.query(subquery).order_by(subquery.c.nom_habitat.asc()).all()

    return [
        {"id_habitat": id_habitat, "nom_habitat": nom_habitat} for id_habitat, nom_habitat in data
    ]


@adresses.route("/idNomRangs", methods=["GET"])
@json_resp
def get_id_nom_rangs():
    """
    Retourne un dictionnaire contenant la liste des id des rangs et leur nom associé,
    trié par ordre alphabétique sur les noms.
    """
    subquery = (
        db.session.query(BibTaxrefRangs.id_rang, BibTaxrefRangs.nom_rang).distinct(
            BibTaxrefRangs.id_rang
        )
    ).subquery()

    data = db.session.query(subquery).order_by(subquery.c.nom_rang.asc()).all()

    return [{"id_rang": id_rang, "nom_rang": nom_rang} for id_rang, nom_rang in data]


@adresses.route("/groupe1_inpn", methods=["GET"])
@json_resp
def get_group1_inpn_taxref():
    """
    Retourne la liste des groupes 1 inpn
    """
    data = (
        db.session.query(Taxref.group1_inpn)
        .distinct(Taxref.group1_inpn)
        .filter(Taxref.group1_inpn != None)
    ).all()
    return ["Non renseigné"] + [d[0] for d in data]


@adresses.route("/groupe2_inpn", methods=["GET"])
@json_resp
def get_group2_inpn_taxref():
    """
    Retourne la liste des groupes 2 inpn
    """
    data = (
        db.session.query(Taxref.group2_inpn)
        .distinct(Taxref.group2_inpn)
        .filter(Taxref.group2_inpn != None)
    ).all()
    return ["Non renseigné"] + [d[0] for d in data]


@adresses.route("/groupe3_inpn", methods=["GET"])
@json_resp
def get_group3_inpn_taxref():
    """
    Retourne la liste des groupes 3 inpn
    """
    data = (
        db.session.query(Taxref.group3_inpn)
        .distinct(Taxref.group3_inpn)
        .filter(Taxref.group3_inpn != None)
    ).all()
    return [d[0] for d in data]


@adresses.route("/allnamebylist/<int(signed=True):id_liste>", methods=["GET"])
@adresses.route("/allnamebylist", methods=["GET"])
@json_resp
def get_AllTaxrefNameByListe(id_liste=None):
    """
    Route utilisée pour les autocompletes
    Si le paramètre search_name est passé, la requête SQL utilise l'algorithme
    des trigrammes pour améliorer la pertinence des résultats
    Route utilisée par le mobile pour remonter la liste des taxons
    params URL:
        - id_liste : identifiant de la liste (si id_liste est null ou = à -1 on ne prend pas de liste)
    params GET (facultatifs):
        - code_liste : code de la liste à filtrer, n'est pris en compte que si aucune liste est spécifiée
        - search_name : nom recherché. Recherche basée sur la fonction
            ilike de SQL avec un remplacement des espaces par %
        - regne : filtre sur le règne INPN
        - group2_inpn : filtre sur le groupe 2 de l'INPN
        - limit: nombre de résultats
        - offset: numéro de la page
    """
    # Traitement des cas ou code_liste = -1
    if id_liste == -1:
        id_liste = None

    q = db.session.query(VMTaxrefListForautocomplete)
    if id_liste:
        q = q.join(BibNoms, BibNoms.cd_nom == VMTaxrefListForautocomplete.cd_nom).join(
            CorNomListe,
            and_(CorNomListe.id_nom == BibNoms.id_nom, CorNomListe.id_liste == id_liste),
        )
    elif request.args.get("code_liste"):
        q = (
            db.session.query(BibListes.id_liste).filter(
                BibListes.code_liste == request.args.get("code_liste")
            )
        ).one()
        id_liste = q[0]

    search_name = request.args.get("search_name")
    if search_name:
        q = q.add_columns(
            func.similarity(VMTaxrefListForautocomplete.unaccent_search_name, search_name).label(
                "idx_trgm"
            )
        )
        search_name = search_name.replace(" ", "%")
        q = q.filter(
            VMTaxrefListForautocomplete.unaccent_search_name.ilike(
                func.unaccent("%" + search_name + "%")
            )
        ).order_by(desc("idx_trgm"))
        q = q.order_by(
            desc(VMTaxrefListForautocomplete.cd_nom == VMTaxrefListForautocomplete.cd_ref)
        )
    # if no search name, no need to order by trigram or cd_nom=cdref - order by PK (used for mobile app)
    else:
        q = q.order_by(VMTaxrefListForautocomplete.gid)

    regne = request.args.get("regne")
    if regne:
        q = q.filter(VMTaxrefListForautocomplete.regne == regne)

    group2_inpn = request.args.get("group2_inpn")
    if group2_inpn:
        q = q.filter(VMTaxrefListForautocomplete.group2_inpn == group2_inpn)

    group3_inpn = request.args.get("group3_inpn")
    if group3_inpn:
        q = q.filter(VMTaxrefListForautocomplete.group3_inpn == group3_inpn)

    limit = request.args.get("limit", 20, int)
    page = request.args.get("page", 1, int)
    if "offset" in request.args:
        warn(
            "offset is deprecated, please use page for pagination (start at 1)", DeprecationWarning
        )
        page = (int(request.args["offset"]) / limit) + 1
    data = q.paginate(page=page, per_page=limit, error_out=False)

    if search_name:
        return [d[0].as_dict(exclude=["unaccent_search_name"]) for d in data.items]
    else:
        return [d.as_dict(exclude=["unaccent_search_name"]) for d in data.items]


@adresses.route("/bib_habitats", methods=["GET"])
@json_resp
def get_bib_hab():
    data = db.session.query(BibTaxrefHabitats).all()
    return [d.as_dict() for d in data]


@adresses.route("/addTaxon", methods=["POST"])
def add_taxon():
    """
    Route utilisée pour insérer un nouveau taxon en bdd
    params POST :
        - objet représentant les données d'un taxon à ajouter.
        - save: boolean qui détermine si le taxon doit être enregistré ou juste vérifié.
    """
    try:
        newTaxon = request.get_json()
        save = newTaxon.get("save", False)  # Récupère 'save' ou False si non défini

        # Convertir uniquement certains attributs à vérifier en minuscule pour la comparaison
        lb_nom = newTaxon.get("lb_nom").lower()
        lb_auteur = newTaxon.get("lb_auteur").lower()
        nom_complet = newTaxon.get("nom_complet").lower()
        nom_valide = newTaxon.get("nom_valide").lower()
        nom_vern = newTaxon.get("nom_vern").lower()
        nom_vern_eng = newTaxon.get("nom_vern_eng").lower()
        url = newTaxon.get("url").lower()

        # Vérifier si un taxon similaire existe déjà dans la base de données
        existing_taxon = (
            db.session.query(Taxref)
            .filter(
                db.func.lower(Taxref.lb_nom) == lb_nom,
                db.func.lower(Taxref.lb_auteur) == lb_auteur,
                db.func.lower(Taxref.nom_complet) == nom_complet,
                db.func.lower(Taxref.nom_valide) == nom_valide,
                db.func.lower(Taxref.nom_vern) == nom_vern,
                db.func.lower(Taxref.nom_vern_eng) == nom_vern_eng,
                db.func.lower(Taxref.url) == url,
                Taxref.regne == newTaxon.get("regne"),
                Taxref.phylum == newTaxon.get("phylum"),
                Taxref.classe == newTaxon.get("classe"),
                Taxref.ordre == newTaxon.get("ordre"),
                Taxref.famille == newTaxon.get("famille"),
                Taxref.sous_famille == newTaxon.get("sous_famille"),
                Taxref.tribu == newTaxon.get("tribu"),
                Taxref.id_statut == newTaxon.get("id_statut"),
                Taxref.id_habitat == newTaxon.get("id_habitat"),
                Taxref.id_rang == newTaxon.get("id_rang"),
                Taxref.group1_inpn == newTaxon.get("group1_inpn"),
                Taxref.group2_inpn == newTaxon.get("group2_inpn"),
            )
            .first()
        )

        if existing_taxon:
            return (
                jsonify(
                    {
                        "error": "Doublon en bdd",
                        "message": "Le taxon existe déjà dans la base de données.",
                    }
                ),
                409,
            )

        # Calculer la prochaine valeur négative pour cd_nom
        next_cd_nom = db.session.query(
            db.func.coalesce(db.func.min(Taxref.cd_nom), 0) - 1
        ).scalar()

        # Créer les nouveaux enregistrements
        add_Taxref = Taxref(
            cd_nom=next_cd_nom,
            cd_ref=next_cd_nom,
            lb_nom=newTaxon.get("lb_nom"),
            lb_auteur=newTaxon.get("lb_auteur"),
            nom_complet=newTaxon.get("nom_complet"),
            nom_valide=newTaxon.get("nom_valide"),
            nom_vern=newTaxon.get("nom_vern"),
            nom_vern_eng=newTaxon.get("nom_vern_eng"),
            url=newTaxon.get("url"),
            regne=newTaxon.get("regne"),
            phylum=newTaxon.get("phylum"),
            classe=newTaxon.get("classe"),
            ordre=newTaxon.get("ordre"),
            famille=newTaxon.get("famille"),
            sous_famille=newTaxon.get("sous_famille"),
            tribu=newTaxon.get("tribu"),
            id_statut=newTaxon.get("id_statut"),
            id_habitat=newTaxon.get("id_habitat"),
            id_rang=newTaxon.get("id_rang"),
            group1_inpn=newTaxon.get("group1_inpn"),
            group2_inpn=newTaxon.get("group2_inpn"),
        )

        add_CorNomListe_100 = CorNomListe(
            id_liste=100,
            id_nom=next_cd_nom,
        )

        add_CorNomListe_101 = CorNomListe(
            id_liste=101,
            id_nom=next_cd_nom,
        )

        add_BibNoms = BibNoms(
            cd_nom=next_cd_nom,
            cd_ref=next_cd_nom,
            nom_francais=newTaxon.get("nom_vern"),
        )

        if not save:
            return (
                jsonify(
                    {
                        "error": "correct",
                        "message": "Aucune erreur détectée. Le taxon peut être ajouté après vérification de doublons au sein même du fichier",
                    }
                ),
                200,
            )

        db.session.add(add_Taxref)
        db.session.add(add_CorNomListe_100)
        db.session.add(add_CorNomListe_101)
        db.session.add(add_BibNoms)
        db.session.commit()

        return jsonify({"message": "Taxon ajouté avec succès !"}), 201

    except Exception as e:
        # En cas d'erreur, renvoyer le message d'erreur
        return (
            jsonify(
                {
                    "error": "Autre erreur (le plus souvent une erreur de syntaxe, l'oubli d'un attribut, etc.)",
                    "message": str(e),
                }
            ),
            500,
        )


### Fonctions Utiles ###


def genericTaxrefList(inBibtaxon, parameters):
    q = Taxref.query.options(raiseload("*"), joinedload(Taxref.bib_nom).joinedload(BibNoms.listes))

    nbResultsWithoutFilter = q.count()

    id_liste = request.args.get("id_liste", type=str, default=[])
    if id_liste and id_liste != "-1":
        id_liste = id_liste.split(",")
        filter_cor_nom_liste = aliased(CorNomListe)
        filter_bib_noms = aliased(BibNoms)
        q = q.join(filter_bib_noms, filter_bib_noms.cd_nom == Taxref.cd_nom)
        q = q.join(filter_cor_nom_liste, filter_bib_noms.id_nom == filter_cor_nom_liste.id_nom)
        q = q.filter(filter_cor_nom_liste.id_liste.in_(tuple(id_liste)))

    if inBibtaxon is True:
        q = q.filter(BibNoms.cd_nom.isnot(None))

    # Traitement des parametres
    limit = parameters.get("limit", 20, int)
    page = parameters.get("page", 1, int)

    for param in parameters:
        if hasattr(Taxref, param) and parameters[param] != "":
            col = getattr(Taxref, param)
            q = q.filter(col == parameters[param])
        elif param == "is_ref" and parameters[param] == "true":
            q = q.filter(Taxref.cd_nom == Taxref.cd_ref)
        elif param == "ilike":
            q = q.filter(Taxref.lb_nom.ilike(parameters[param] + "%"))
        elif param == "is_inbibtaxons" and parameters[param] == "true":
            q = q.filter(BibNoms.cd_nom.isnot(None))
        elif param.split("-")[0] == "ilike":
            value = unquote(parameters[param])
            column = str(param.split("-")[1])
            col = getattr(Taxref, column)
            q = q.filter(col.ilike(value + "%"))

    nbResults = q.count()

    # Order by
    if "orderby" in parameters:
        if getattr(Taxref, parameters["orderby"], None):
            orderCol = getattr(Taxref, parameters["orderby"])
        else:
            orderCol = None
        if "order" in parameters and orderCol:
            if parameters["order"] == "desc":
                orderCol = orderCol.desc()
        q = q.order_by(orderCol)

    # Filtrer champs demandés par la requête
    fields = request.args.get("fields", type=str, default=[])
    if fields:
        fields = fields.split(",")
    fields_to_filter = None
    if fields:
        fields_to_filter = [f for f in fields if getattr(Taxref, f, None)]

    results = q.paginate(page=page, per_page=limit, error_out=False)

    items = []
    for r in results.items:
        data = r.as_dict(fields=fields_to_filter)
        if not fields or "listes" in fields:
            id_listes = []
            if r.bib_nom:
                id_listes = [l.id_liste for l in r.bib_nom[0].listes]
            data = dict(data, listes=id_listes)
        if not fields or "id_nom" in fields:
            id_nom = None
            if r.bib_nom:
                id_nom = r.bib_nom[0].id_nom
            data = dict(data, id_nom=id_nom)

        items.append(data)

    return {
        "items": items,
        "total": nbResultsWithoutFilter,
        "total_filtered": nbResults,
        "limit": limit,
        "page": page,
    }


def genericHierarchieSelect(tableHierarchy, rang, parameters):
    dfRang = tableHierarchy.__table__.columns["id_rang"]
    q = db.session.query(tableHierarchy).filter(tableHierarchy.id_rang == rang)

    limit = parameters.get("limit", 100, int)

    for param in parameters:
        if param in tableHierarchy.__table__.columns:
            col = getattr(tableHierarchy.__table__.columns, param)
            q = q.filter(col == parameters[param])
        elif param == "ilike":
            q = q.filter(tableHierarchy.__table__.columns.lb_nom.ilike(parameters[param] + "%"))

    results = q.limit(limit).all()
    return results
