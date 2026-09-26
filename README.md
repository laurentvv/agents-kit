# agents-kit

**Base commune `AGENTS.md` versionnée + script de synchronisation**, pour piloter une flotte de dépôts avec des agents IA de codage (ZCode, Claude Code, Codex, Cursor, Windsurf…). Écrit en français, pensé Windows + `uv`, sans aucune dépendance.

## Le problème

Quand on travaille avec des agents IA sur plusieurs dépôts, le fichier `AGENTS.md` (instructions injectées à chaque session) finit copié-collé partout. Le constat d'un audit de 24 fichiers réels :

- **dérive** : le même socle existe en 8 variantes (rotation de log différente, emplacements divergents, formats inégaux) ;
- **corruption** : des exports mal échappés rendent le markdown illisible pour l'agent ;
- **redondance** : les mêmes règles (Git, secrets, validation) réécrites différemment dans chaque dépôt ;
- **poids** : de 157 octets inutiles à 56 Ko consommés à chaque session.

## La solution : un bloc commun délimité, resynchronisable

Chaque `AGENTS.md` devient **deux zones** :

```text
AGENTS.md d'un dépôt
├── <!-- BEGIN:agents-commun v1.0 -->   ← bloc géré, identique partout,
│      §1 Environnement                    remplacé par le script
│      §2 État sur disque (4 fichiers)
│      §3 Boucle d'exécution (gate)
│      §4 Git & livraison
│      §5 Sécurité & intégrité
│      §6 Vérité & validation
├── <!-- END:agents-commun -->
└── §7 Spécifique projet                ← libre, préservé par le script
```

C'est le même mécanisme que les blocs gérés **Next.js** et **OpenSpec** : des marqueurs HTML neutres pour le markdown, qu'un script sait remplacer sans rien toucher d'autre.

## Contenu de la base commune (v1.0)

1. **Environnement** — Windows, shell déclaré, `uv` uniquement, zéro chemin machine en dur.
2. **État sur disque = source de vérité** — le « ledger » en 4 fichiers (`feature_list.json`, `contract.md`, `progress.md`, `log.md`) : formats stricts, budget ~200 caractères par entrée de log, rotation mensuelle + par taille, variante « base DuckDB/SQLite » documentée.
3. **Boucle d'exécution** — Bootstrap → Action → **Gate** (pas de sync si la vérification statique échoue) → Synchronisation → Erreurs.
4. **Git & livraison** — jamais `main` direct, PR puis arrêt, jamais `reset --hard` vivant, checklist avant commit.
5. **Sécurité & intégrité** — zéro secret, reformulation obligatoire avant toute suppression ambiguë, zéro extinction machine, validation humaine avant action irréversible.
6. **Vérité & validation** — « vérifié » = exécuté ou regardé, jamais déduit des logs ; re-test par le chemin complet réel.

Chaque dépôt ajoute son **§7 spécifique** : mission, commandes clés, invariants métier, pièges datés, renvois vers un `PROJECT_MEMORY.md` pour le contexte long.

## Démarrage rapide

```bash
git clone https://github.com/laurentvv/agents-kit.git
cd agents-kit

# État de votre flotte (par défaut : le dossier parent des dépôts)
uv run --no-project python scripts/sync_agents.py audit          # ou : python scripts/sync_agents.py audit

# Instancier un nouveau dépôt (AGENTS.md + les 4 fichiers d'état)
uv run --no-project python scripts/sync_agents.py init ../mon-projet --nom "Mon Projet" --ledger
```

## Commandes

| Commande | Rôle |
|---|---|
| `audit [racine]` | Classe chaque `<racine>/<dépôt>/AGENTS.md` : à jour · dérivé · généré (OpenSpec/Next.js — à ignorer) · corrompu · non géré |
| `check <dépôt>` | Le bloc commun de ce dépôt est-il identique au canonique ? (exit 1 si dérive) |
| `sync <dépôt>` | Remplace le bloc entre marqueurs par le canonique, préserve le spécifique |
| `init <dépôt> [--nom N] [--force] [--ledger]` | Crée `AGENTS.md` depuis le template ; `--ledger` ajoute les 4 fichiers d'état manquants |

`check`/`sync` acceptent `--fichier <chemin>` pour cibler autre chose que `AGENTS.md` (le kit s'en sert pour rafraîchir son propre template). Tout est stdlib, Python 3.11+.

## Faire évoluer la base commune

1. Modifier `agents-commun.md` (monter la version dans le marqueur `BEGIN:agents-commun vX.Y`).
2. Rafraîchir le template du kit : `uv run --no-project python scripts/sync_agents.py sync . --fichier template/AGENTS.template.md`
3. `audit` pour repérer les dépôts « dérivés », puis `sync <dépôt>` un par un, commit par dépôt.
4. Toute évolution du commun doit être générique (aucun chemin machine, aucun nom de dépôt) — le spécifique vit au §7.

## Compatibilité

- **Blocs générés** (OpenSpec, Next.js) : ils gèrent leurs propres marqueurs, les nôtres coexistent dans le même fichier. `audit` les classe « générés » et ne les touche jamais.
- **Dépôts vendés** (`vendor/`, sauvegardes figées) : à exclure de la synchronisation.
- **Langue** : français par design (les instructions sont relues par un humain francophone avant d'être appliquées par l'agent).

## Structure du dépôt

```text
agents-kit/
├── agents-commun.md              ← le canon (bloc délimité, versionné)
├── template/AGENTS.template.md   ← gabarit complet (commun + §7 à remplir)
├── scripts/sync_agents.py        ← audit / check / sync / init (stdlib)
├── docs/audit-2026-09-26.md      ← l'audit initial (24 fichiers réels)
├── docs/MIGRATION.md             ← plan d'action dépôt par dépôt
├── AGENTS.md                     ← le kit dogfoode sa propre base
└── LICENSE                       ← MIT
```

## Licence

[MIT](LICENSE) — reprenez le bloc, adaptez le §7, gardez les marqueurs.
