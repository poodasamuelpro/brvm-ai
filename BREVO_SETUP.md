# Suivi Brevo — brvm-ai

Dernière mise à jour : 2026-10-08 (UTC)

Configuration utilisée par **GitHub Actions** : dépôt → **Settings → Secrets and variables → Actions**. Les valeurs secrètes ne sont volontairement pas inscrites dans ce document ni dans Git.

| Nom | Type GitHub | État | À faire |
|---|---|---|---|
| `BREVO_API_KEY` | Secret | **FAUX / placeholder** | Remplacer par la clé API Brevo réelle |
| `BREVO_SMTP_LOGIN` | Secret | **FAUX / placeholder** | Remplacer par le login SMTP Brevo réel |
| `BREVO_SMTP_KEY` | Secret | **FAUX / placeholder** | Remplacer par la clé SMTP Brevo réelle |
| `BREVO_SENDER_EMAIL` | Variable facultative | **FAUX / placeholder** | Mettre une adresse expéditeur vérifiée, ou supprimer la variable pour utiliser le repli du workflow |

**Repli expéditeur codé dans le workflow :** `speedconnectouaga@gmail.com`.

**Destinataires codés dans le workflow :** `MAIL_TO=speedconnectouaga@gmail.com`, `MAIL_CC=theyoung0910@gmail.com`. Ils ne sont pas à ajouter dans les paramètres Actions.

## Historique

- 2026-10-08 : les quatre entrées Actions ont été créées avec des valeurs factices pour préparer leur remplacement. Aucun workflow n’a été lancé.
- 2026-10-08 : création de ce document de suivi à la racine du dépôt.

**Sécurité :** remplacer les placeholders dans GitHub Actions; ne jamais coller les vraies clés dans ce fichier, le code ou Git.
