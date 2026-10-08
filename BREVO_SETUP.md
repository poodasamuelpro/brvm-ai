# Suivi Brevo — brvm-ai

Dernière mise à jour : 2026-10-08 (UTC)

## Statut du projet

**EN CONSTRUCTION — projet personnel; pas de configuration SMTP requise.** Aucun identifiant Brevo SMTP n’est configuré. Les placeholders API/SMTP et l’adresse expéditeur factice ont été retirés pour que les workflows ignorent l’envoi tant que le projet n’est pas prêt.

| Élément GitHub Actions | État actuel | À faire |
|---|---|---|
| `BREVO_API_KEY` | Non configurée | Ajouter une clé API Brevo valide seulement lorsqu’une fonction e-mail doit être activée |
| `BREVO_SMTP_LOGIN` | Non configuré | Non requis : pas de SMTP |
| `BREVO_SMTP_KEY` | Non configurée | Non requis : pas de SMTP |
| `BREVO_SENDER_EMAIL` | Variable factice supprimée | Repli du workflow utilisé; choisir une adresse vérifiée lors de l’activation de l’envoi |

La clé candidate examinée dans la conversation ne peut pas être associée à un compte ou à un projet : elle est incomplète selon le format attendu et l’API Brevo répond HTTP 401. Elle n’a donc pas été enregistrée ni réutilisée. Aucune clé d’un autre dépôt n’a été copiée ici.

## Historique

- 2026-10-08 : confirmé comme projet personnel en cours de construction; pas de besoin SMTP.
- 2026-10-08 : placeholders `BREVO_API_KEY`, `BREVO_SMTP_LOGIN`, `BREVO_SMTP_KEY` et `BREVO_SENDER_EMAIL` retirés.
- 2026-10-08 : clé candidate testée en lecture seule, réponse HTTP 401 et format incomplet; non enregistrée.
- Aucun workflow ni e-mail n’a été lancé.

À réévaluer lorsque le projet sera prêt à envoyer des courriels par API.
