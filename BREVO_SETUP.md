# Suivi e-mail — brvm-ai

Dernière mise à jour : 2026-10-08 (UTC)

## Statut

**EN CONSTRUCTION — projet personnel; aucun SMTP requis.** Les placeholders Brevo ont été retirés. Aucun e-mail ni workflow de test n’a été lancé.

| Élément | État GitHub Actions | Suite |
|---|---|---|
| `BREVO_API_KEY` | Non configurée | Ajouter une clé API valide seulement si une fonction e-mail doit être activée |
| `BREVO_SMTP_LOGIN` | Non configuré | Non requis : pas de SMTP |
| `BREVO_SMTP_KEY` | Non configurée | Non requis : pas de SMTP |
| `BREVO_SENDER_EMAIL` | Placeholder supprimé | Définir une adresse expéditeur vérifiée lorsque l’envoi sera activé |

## Contrôle de la clé candidate NYME

La clé transmise le 2026-10-08 correspond au format courant `xkeysib-…`, mais Brevo a répondu **HTTP 401** à la requête de lecture seule `GET /v3/account`. La clé n’a pas été ajoutée à GitHub Actions et aucune information de compte, adresse ou domaine ne peut être déduite de cette réponse. Aucun secret d’un autre projet n’a été copié.

## Historique

- 2026-10-08 : placeholders API/SMTP et variable expéditeur retirés; SMTP non requis.
- 2026-10-08 : clé candidate NYME testée en lecture seule; HTTP 401, non enregistrée.
- Aucun courriel ni workflow n’a été déclenché.

À réévaluer lorsque le projet sera prêt et qu’une clé Brevo valable pour le compte concerné sera disponible.
