# Plan de migration des dépôts vers agents-kit

Issue de l'audit du 2026-09-26 (`docs/audit-2026-09-26.md`). Chaque migration suit le même geste :

1. `init <dépôt> --force` **ou** remplacement manuel du bloc socle par le bloc commun (selon la richesse du spécifique) ;
2. rédaction du §7 spécifique (reprendre le contenu métier existant, alléger le contexte long vers `PROJECT_MEMORY.md` / `docs/`) ;
3. `check <dépôt>` au vert, puis `audit` pour confirmer ;
4. commit par dépôt (`chore: agents-kit v1.0 — bloc commun + spécifique`).

## Vague 1 — corrompus, doublons et vides (gain immédiat)

| Dépôt | Action |
|---|---|
| `disk-clean` | Réécrire : bloc commun + §7 minimal (mission, commandes) — le fichier actuel est corrompu et 100 % générique |
| `compare-graph-generator` | Idem `disk-clean` (doublon octet-identique corrompu) |
| `blender-ia` | Réécrire le corrompu ; conserver la section « Règle de Vérification avant Livraison » (rendu GPU HIP/CPU, `blender_run.py --device`) en §7 |
| `Laya` | Remplacer la copie générique : commun + §7 (5-10 lignes réelles) |
| `YouTubeToMP3` | Idem `Laya` (préciser le venv yt-dlp et les cookies anti-bot au §7) |
| `alerte-wti` | `init --ledger` puis compléter §7 (env Windows + `.venv` de trading_bot) |

## Vague 2 — socle à remplacer, métier à conserver

| Dépôt | Action |
|---|---|
| `web-assets` | Remplacer le socle périmé (pas de rotation) ; §7 : Scriptorium 8787, base `data/app.db` |
| `video-analys-ia` | Remplacer la partie socle ; §7 : §0 « mission finale » (analyser → répliquer), écosystème |
| `roblox` | Remplacer le socle (ses améliorations — budget 200 cars, gate statique, `awaiting_playtest` — sont intégrées au commun v1) ; §7 : KB NotebookLM, hygiène assets, norme graphique |
| `L'HERITIER DU VIDE` (C:\test) | Séparer : spec générique → commun ; métier Godot/pièges/3D/DuckDB assets/Fab → §7 (+ éventuellement `PROJECT_MEMORY.md` pour le contexte long) |

## Vague 3 — allègement et déduplication

| Dépôt | Action |
|---|---|
| `ai-doc2video` | Alléger (56 Ko) : déplacer commandes TTS détaillées, protocole OAuth, playlists vers `docs/memory_bank/` ; §7 = boussole + 26 règles resserrées ; écosystème → source unique partagée avec generator-assets |
| `generator-assets` | Extraire la cartographie écosystème vers la source unique ; §7 : contrat consommateurs, veille, process maj/rollback |
| `fire_UI` | Conserver le bloc Next.js géré en tête ; intégrer le commun ; §7 : PowerShell déclaré, stack figée, garde `patrimoine.db` |

## Vague 4 — alignement léger (déjà bons)

| Dépôt | Action |
|---|---|
| `jardin-os` | Déjà conforme au modèle 2 niveaux — sert de référence ; optionnel : `check` en marque-page |
| `my-claw`, `ComfyUI-Majoor-OmniCam`, `Trading-AI` | Optionnel : adopter le bloc commun pour Git/sécurité/vérité, garder leur structure propre en §7 |
| `graph-orchestrator-smolagents` | Conserver la variante DuckDB (documentée comme variante B du commun) ; §7 : périmètre usine/produits |

## À ne PAS migrer

| Cible | Raison |
|---|---|
| `pdf-ocr-ai` / `pdf-to-md-ocr` (racine + `openspec/`) | Blocs gérés OpenSpec — `openspec update` uniquement ; jamais à la main |
| `Trading-AI/vendor/timesfm` | Dépôt Google vendé |
| `video-analys-ia_sauvegarde_etat_2026-09-16` | Sauvegarde figée par conception |

## Après migration

- `uv run --no-project python scripts/sync_agents.py audit` ne doit plus montrer que : « à jour » (dépôts gérés), « généré » (OpenSpec/Next.js) et les exclusions.
- Toute évolution future du commun : éditer `agents-commun.md`, monter la version, resynchroniser le template du kit, puis `sync` dépôt par dépôt.
