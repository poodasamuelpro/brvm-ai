"""Pipeline de collecte des cours de fin de séance BRVM vers le schéma PostgreSQL `brvm`.

Chaîne : page officielle → instantané brut (`source_document`) → une ligne brute par
valeur (`raw_ingest_record`) → validation → normalisation (`market_bar`) → constats
(`data_quality_issue`) → suivi d’exécution (`pipeline_run`). Tout est écrit dans une
seule transaction : en cas d’erreur, rien n’est conservé partiellement.

Idempotence : un instantané identique (même séance, même contenu de tableau) n’est
jamais réinséré. Une valeur déjà enregistrée pour la même séance avec des chiffres
différents est conservée en `quarantined` avec un constat `revision_source`.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, datetime, time, timedelta
from typing import TYPE_CHECKING, Any
from uuid import UUID

from brvm_ia.collecte.sources.donnees_marche import (
    CODE_SOURCE_BRVM,
    FUSEAU_BRVM,
    URL_COURS_ACTIONS,
    PageCoursActions,
)
from brvm_ia.collecte.validateurs import CoursNormalise, ResultatLigne, valider_page
from brvm_ia.exceptions import ErreurBaseDeDonnees

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

    from brvm_ia.base_de_donnees.moteur import GestionnaireBaseDeDonnees

CODE_PIPELINE = "collecte_brvm_cours_actions"
VERSION_PIPELINE = "1"
NATURE_JEU = "brvm_cours_actions_fin_seance"
INTERVALLE = "1d"
CODE_MARCHE = "BRVM"
NOM_MARCHE = "Bourse Régionale des Valeurs Mobilières"
# Les cours sont publiés en « FCFA » par la BRVM ; le code ISO 4217 de l’UEMOA est XOF.
DEVISE = ("XOF", "Franc CFA (UEMOA)")
_GRAVITE_SQL = {"warning": "warning", "error": "error"}


@dataclass(frozen=True, slots=True)
class BilanCollecte:
    """Résumé d’une exécution, sans données sensibles."""

    date_seance: str
    deja_collecte: bool
    lignes_recues: int
    barres_inserees: int
    barres_identiques_ignorees: int
    barres_en_quarantaine: int
    lignes_rejetees: int
    nouvelles_valeurs: int
    source_document_id: UUID | None


def _sha256_json(objet: Any) -> str:
    texte = json.dumps(objet, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(texte.encode("utf-8")).hexdigest()


class PipelineCoursBRVM:
    """Enregistre un instantané de la page « Cours des actions » de la BRVM."""

    def __init__(self, gestionnaire: GestionnaireBaseDeDonnees) -> None:
        self._gestionnaire = gestionnaire

    def enregistrer(
        self, page: PageCoursActions, maintenant: datetime | None = None
    ) -> BilanCollecte:
        instant = maintenant or datetime.now(UTC)
        date_seance, resultats = valider_page(page, instant)
        identifiant_externe = f"cours-actions:{date_seance.isoformat()}:{page.empreinte_tableau}"

        with self._gestionnaire.session() as session:
            source_id = self._assurer_source(session)
            existant = self._scalaire(
                session,
                "SELECT source_document_id FROM brvm.source_document "
                "WHERE source_id = :s AND external_identifier = :e",
                s=source_id,
                e=identifiant_externe,
            )
            if existant is not None:
                # Jour sans nouvelle séance (week-end, férié) ou relance : aucune écriture
                # de données, mais l’exécution est tracée comme réussie sans effet.
                run_id = self._demarrer_run(session, date_seance.isoformat(), page)
                self._terminer_run(session, run_id, "succeeded", len(resultats), 0, None)
                return BilanCollecte(
                    date_seance.isoformat(), True, len(resultats), 0, 0, 0, 0, 0, existant
                )

            marche_id = self._assurer_marche(session)
            run_id = self._demarrer_run(session, date_seance.isoformat(), page)
            document_id = self._identifiant(
                session,
                """
                INSERT INTO brvm.source_document
                    (source_id, external_identifier, source_url, mime_type, content_sha256,
                     published_at, retrieved_at)
                VALUES (:s, :e, :u, 'text/html', :h, :p, :r)
                RETURNING source_document_id
                """,
                s=source_id,
                e=identifiant_externe,
                u=page.url,
                h=page.contenu_sha256,
                p=page.mise_a_jour_source,
                r=page.recupere_le,
            )
            self._executer(
                session,
                "INSERT INTO brvm.pipeline_run_source (pipeline_run_id, source_id, "
                "source_document_id) VALUES (:r, :s, :d)",
                r=run_id,
                s=source_id,
                d=document_id,
            )

            compteurs = {"inserees": 0, "identiques": 0, "quarantaine": 0, "rejetees": 0, "nouv": 0}
            for resultat in resultats:
                self._traiter_ligne(
                    session, resultat, page, source_id, document_id, marche_id, compteurs
                )

            self._terminer_run(
                session, run_id, "succeeded", len(resultats), compteurs["rejetees"], None
            )

        return BilanCollecte(
            date_seance=date_seance.isoformat(),
            deja_collecte=False,
            lignes_recues=len(resultats),
            barres_inserees=compteurs["inserees"],
            barres_identiques_ignorees=compteurs["identiques"],
            barres_en_quarantaine=compteurs["quarantaine"],
            lignes_rejetees=compteurs["rejetees"],
            nouvelles_valeurs=compteurs["nouv"],
            source_document_id=document_id,
        )

    # -- Étapes -------------------------------------------------------------------------

    def _traiter_ligne(
        self,
        session: Session,
        resultat: ResultatLigne,
        page: PageCoursActions,
        source_id: UUID,
        document_id: UUID,
        marche_id: UUID,
        compteurs: dict[str, int],
    ) -> None:
        cellules = resultat.ligne.en_dictionnaire()
        charge_utile = {
            "cellules": cellules,
            "page_mise_a_jour": page.mise_a_jour_source.isoformat(),
            "page_seance_fermee": page.seance_fermee,
            "constats": [
                {"regle": c.regle, "gravite": c.gravite, "description": c.description}
                for c in resultat.constats
            ],
        }
        cle = f"{cellules['Symbole'] or '?'}:{page.mise_a_jour_source.date().isoformat()}"
        raw_id = self._identifiant(
            session,
            """
            INSERT INTO brvm.raw_ingest_record
                (source_id, source_document_id, dataset_kind, source_record_key, raw_payload,
                 payload_sha256, published_at, processing_status, processed_at)
            VALUES (:s, :d, :k, :c, CAST(:p AS jsonb), :h, :pub, :st, clock_timestamp())
            RETURNING raw_ingest_record_id
            """,
            s=source_id,
            d=document_id,
            k=NATURE_JEU,
            c=cle,
            p=json.dumps(charge_utile, ensure_ascii=False),
            h=_sha256_json(cellules),
            pub=page.mise_a_jour_source,
            st="rejected" if resultat.est_rejetee else "normalized",
        )

        if resultat.cours is None:
            compteurs["rejetees"] += 1
            for constat in resultat.constats:
                if constat.gravite in _GRAVITE_SQL:
                    self._constat(
                        session,
                        "raw_ingest_record_id",
                        raw_id,
                        constat.regle,
                        _GRAVITE_SQL[constat.gravite],
                        constat.description,
                        cle,
                    )
            return

        cours = resultat.cours
        security_id, est_nouvelle = self._assurer_valeur(session, cours, marche_id, document_id)
        compteurs["nouv"] += int(est_nouvelle)

        precedent = session.execute(
            self._texte(
                """
                SELECT opening_price, closing_price, volume FROM brvm.market_bar
                WHERE security_id = :sec AND source_id = :s AND interval_code = :i
                  AND market_date = :m AND validation_status = 'validated'
                ORDER BY collected_at DESC LIMIT 1
                """
            ),
            {"sec": security_id, "s": source_id, "i": INTERVALLE, "m": cours.date_seance},
        ).first()
        revision = False
        if precedent is not None:
            if (precedent[0], precedent[1], precedent[2]) == (
                cours.ouverture,
                cours.cloture,
                cours.volume,
            ):
                compteurs["identiques"] += 1
                return
            revision = True

        avertissements = [c for c in resultat.constats if c.gravite == "warning"]
        statut = "quarantined" if (avertissements or revision) else "validated"
        debut = datetime.combine(cours.date_seance, time.min, tzinfo=FUSEAU_BRVM)
        bar_id = self._identifiant(
            session,
            """
            INSERT INTO brvm.market_bar
                (security_id, source_id, raw_ingest_record_id, interval_code, period_start,
                 period_end, market_date, opening_price, closing_price, volume,
                 validation_status, published_at)
            VALUES (:sec, :s, :raw, :i, :deb, :fin, :m, :o, :c, :v, :st, :pub)
            RETURNING market_bar_id
            """,
            sec=security_id,
            s=source_id,
            raw=raw_id,
            i=INTERVALLE,
            deb=debut,
            fin=debut + timedelta(days=1),
            m=cours.date_seance,
            o=cours.ouverture,
            c=cours.cloture,
            v=cours.volume,
            st=statut,
            pub=page.mise_a_jour_source,
        )
        if statut == "validated":
            compteurs["inserees"] += 1
        else:
            compteurs["quarantaine"] += 1
        for constat in avertissements:
            self._constat(
                session, "market_bar_id", bar_id, constat.regle, "warning", constat.description, cle
            )
        if revision:
            self._constat(
                session,
                "market_bar_id",
                bar_id,
                "revision_source",
                "warning",
                "Valeurs différentes d’une barre déjà validée pour la même séance.",
                cle,
            )

    def _assurer_source(self, session: Session) -> UUID:
        return self._identifiant(
            session,
            """
            INSERT INTO brvm.data_source (code, name, source_type, base_url, terms_url)
            VALUES (:c, 'BRVM — site officiel (cours des actions)', 'site_web_officiel', :u, NULL)
            ON CONFLICT (code) DO UPDATE SET code = EXCLUDED.code
            RETURNING source_id
            """,
            c=CODE_SOURCE_BRVM,
            u=URL_COURS_ACTIONS,
        )

    def _assurer_marche(self, session: Session) -> UUID:
        self._executer(
            session,
            "INSERT INTO brvm.currency (currency_code, name) VALUES (:c, :n) "
            "ON CONFLICT (currency_code) DO NOTHING",
            c=DEVISE[0],
            n=DEVISE[1],
        )
        return self._identifiant(
            session,
            """
            INSERT INTO brvm.market (code, name, currency_code, timezone_name)
            VALUES (:c, :n, :d, :tz)
            ON CONFLICT (code) DO UPDATE SET code = EXCLUDED.code
            RETURNING market_id
            """,
            c=CODE_MARCHE,
            n=NOM_MARCHE,
            d=DEVISE[0],
            tz=str(FUSEAU_BRVM),
        )

    def _assurer_valeur(
        self, session: Session, cours: CoursNormalise, marche_id: UUID, document_id: UUID
    ) -> tuple[UUID, bool]:
        """Résout le symbole actif; sinon crée société, titre et historique de symbole.

        `valid_from` du symbole = première séance observée par BRVM-AI (et non la date
        d’introduction en bourse, inconnue de cette source). Le pays n’est pas déduit du nom.
        """
        existant = self._scalaire(
            session,
            """
            SELECT security_id FROM brvm.security_symbol_history
            WHERE market_id = :m AND symbol = :sym AND valid_from <= :d
              AND (valid_to IS NULL OR valid_to >= :d)
            ORDER BY valid_from DESC LIMIT 1
            """,
            m=marche_id,
            sym=cours.symbole,
            d=cours.date_seance,
        )
        if existant is not None:
            return existant, False
        company_id = self._identifiant(
            session,
            "INSERT INTO brvm.company (legal_name) VALUES (:n) RETURNING company_id",
            n=cours.nom,
        )
        security_id = self._identifiant(
            session,
            "INSERT INTO brvm.security (company_id, market_id, currency_code) "
            "VALUES (:c, :m, :d) RETURNING security_id",
            c=company_id,
            m=marche_id,
            d=DEVISE[0],
        )
        self._executer(
            session,
            """
            INSERT INTO brvm.security_symbol_history
                (security_id, market_id, symbol, valid_from, source_document_id)
            VALUES (:sec, :m, :sym, :d, :doc)
            """,
            sec=security_id,
            m=marche_id,
            sym=cours.symbole,
            d=cours.date_seance,
            doc=document_id,
        )
        return security_id, True

    def journaliser_interruption(
        self, statut: str, code_erreur: str, resume: str, parametres: dict[str, Any]
    ) -> None:
        """Trace dans une transaction distincte une exécution échouée ou annulée.

        `resume` doit être un message sûr (aucune URL de connexion ni donnée brute).
        """
        if statut not in {"failed", "cancelled"}:
            raise ValueError("Statut d’interruption non autorisé.")
        with self._gestionnaire.session() as session:
            run_id = self._identifiant(
                session,
                """
                INSERT INTO brvm.pipeline_run
                    (pipeline_definition_id, run_status, parameters, started_at)
                VALUES (:d, 'running', CAST(:p AS jsonb), clock_timestamp())
                RETURNING pipeline_run_id
                """,
                d=self._assurer_definition(session),
                p=json.dumps(parametres, ensure_ascii=False),
            )
            self._executer(
                session,
                "INSERT INTO brvm.pipeline_run_error (pipeline_run_id, error_code, error_type, "
                "safe_summary) VALUES (:r, :c, :t, :s)",
                r=run_id,
                c=code_erreur,
                t=statut,
                s=resume,
            )
            self._terminer_run(session, run_id, statut, 0, 0, resume)

    def _terminer_run(
        self,
        session: Session,
        run_id: UUID,
        statut: str,
        lignes: int,
        rejets: int,
        resume: str | None,
    ) -> None:
        self._executer(
            session,
            """
            UPDATE brvm.pipeline_run
            SET run_status = :st, finished_at = clock_timestamp(),
                rows_processed = :p, rows_rejected = :j, safe_error_summary = :e
            WHERE pipeline_run_id = :r
            """,
            st=statut,
            p=lignes,
            j=rejets,
            e=resume,
            r=run_id,
        )

    def _assurer_definition(self, session: Session) -> UUID:
        return self._identifiant(
            session,
            """
            INSERT INTO brvm.pipeline_definition (code, version, description, is_enabled)
            VALUES (:c, :v, 'Collecte des cours de fin de séance publiés par brvm.org', true)
            ON CONFLICT (code, version) DO UPDATE SET code = EXCLUDED.code
            RETURNING pipeline_definition_id
            """,
            c=CODE_PIPELINE,
            v=VERSION_PIPELINE,
        )

    def _demarrer_run(self, session: Session, date_seance: str, page: PageCoursActions) -> UUID:
        definition_id = self._assurer_definition(session)
        return self._identifiant(
            session,
            """
            INSERT INTO brvm.pipeline_run
                (pipeline_definition_id, run_status, parameters, started_at)
            VALUES (:d, 'running', CAST(:p AS jsonb), clock_timestamp())
            RETURNING pipeline_run_id
            """,
            d=definition_id,
            p=json.dumps({"date_seance": date_seance, "url": page.url}),
        )

    def _constat(
        self,
        session: Session,
        colonne_cible: str,
        cible: UUID,
        regle: str,
        gravite: str,
        description: str,
        cle: str,
    ) -> None:
        if colonne_cible not in {"raw_ingest_record_id", "market_bar_id"}:
            raise ValueError("Cible de constat non autorisée.")
        self._executer(
            session,
            f"INSERT INTO brvm.data_quality_issue ({colonne_cible}, rule_code, severity, "
            "description, safe_context) VALUES (:t, :r, :g, :d, CAST(:c AS jsonb))",
            t=cible,
            r=regle,
            g=gravite,
            d=description,
            c=json.dumps({"cle_source": cle}),
        )

    # -- Utilitaires SQL ----------------------------------------------------------------

    @staticmethod
    def _texte(sql: str) -> Any:
        from sqlalchemy import text

        return text(sql)

    def _scalaire(self, session: Session, sql: str, **parametres: Any) -> Any:
        return session.execute(self._texte(sql), parametres).scalar_one_or_none()

    def _identifiant(self, session: Session, sql: str, **parametres: Any) -> UUID:
        valeur = self._scalaire(session, sql, **parametres)
        if not isinstance(valeur, UUID):
            raise ErreurBaseDeDonnees("Identifiant attendu non renvoyé par PostgreSQL.")
        return valeur

    def _executer(self, session: Session, sql: str, **parametres: Any) -> None:
        session.execute(self._texte(sql), parametres)
