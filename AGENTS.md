# AGENTS.md — agents-kit

> Instructions pour tout agent IA de codage travaillant dans ce dépôt.
> Structure : **bloc commun** (délimité, resynchronisable) + **spécifique projet** (libre).

<!-- BEGIN:agents-commun v1.0 — bloc partagé entre dépôts (agents-kit). Ne pas éditer à la main : resynchroniser via scripts/sync_agents.py -->
<!-- Le script remplace uniquement ce qui se trouve entre les marqueurs BEGIN/END ; tout le contenu spécifique du dépôt est préservé -->

## §1 Environnement

- Machine : **Windows 11**. Shell du dépôt : **Git Bash** *(adapter au §7 si PowerShell 7 — n'utiliser QUE les commandes du shell déclaré)*.
- Python : **`uv` uniquement** — jamais `pip install`, jamais `requirements.txt` (`uv add` / `uv run`).
- Chemins machine : jamais en dur dans le code — passer par la configuration du projet (config.py / .env / section dédiée).
- Contexte long (architecture, leçons détaillées, écosystème) : voir `PROJECT_MEMORY.md` ou `docs/` du dépôt — AGENTS.md reste volontairement court.

## §2 État sur disque = source de vérité

Ne jamais se fier à la seule fenêtre de contexte : elle s'altère, se compresse, s'efface. L'état du travail vit dans **quatre fichiers** (défaut : racine du dépôt ; variantes admises si déclarées au §7 : `.agents/`, `memory-bank/`). À chaque initialisation, plantage ou redémarrage : les lire pour reconstruire son état de façon déterministe.

| Fichier | Rôle | Cycle de vie |
|---|---|---|
| `feature_list.json` | Fonctionnalités **actives** (pending / in_progress) uniquement. | Mis à jour à chaque changement de statut ; les `completed` partent en `feature_list_archive.json` (garder court — lu chaque session). |
| `contract.md` | Contrat de validation : assertions strictes et testables (15-30 critères). | **Figé** avant la première ligne de code ; plus modifiable par le générateur. |
| `progress.md` | Tableau de bord du sprint en cours (objectif + jalons). | Mis à jour à la fin de chaque itération. |
| `log.md` | Journal chronologique **append-only**. | Une entrée au début et à la fin de chaque action. |

**Formats** :

`feature_list.json` — `"status"` ∈ `pending | in_progress | completed` (+ extensions projet autorisées, ex. `awaiting_playtest` — les déclarer au §7) :

```json
{ "features": [ { "id": "F-01", "name": "…", "description": "périmètre technique",
  "status": "pending | in_progress | completed", "dependencies": [] } ] }
```

`log.md` — **budget ~200 caractères par entrée** (le détail va dans le commit) :

```markdown
## [AAAA-MM-JJ] init | Initialisation du workspace et négociation du contrat.md
## [AAAA-MM-JJ] gen  | Écriture du script principal et génération des structures JSON.
## [AAAA-MM-JJ] eval | Échec de la validation du contrat sur le critère 2.
```

`type` ∈ `init | gen | eval | fix | sync | done | err` (+ extensions projet).

**Rotation du log** (budget contexte) : `log.md` ne contient que le mois courant. Au changement de mois (ou au-delà de ~150 Ko), déplacer l'historique vers `docs/journal/log_AAAA-MM[_JJ-JJ].md` — rien n'est effacé, l'archive reste grepable. **Au bootstrap : ne lire que `log.md` (court) ; les archives uniquement par `grep` ciblé.** *Variante B (à déclarer au §7) : historisation événementielle en base (DuckDB/SQLite) à la place du fichier plat — même discipline, zéro journal .md.*

## §3 Boucle d'exécution

1. **Bootstrap** — vérifier les 4 fichiers ; absents → les créer ; présents → les lire (budget : actives de `feature_list.json`, `progress.md`, `contract.md`, `log.md` en entier). Ne PAS lire les archives sauf `grep` ciblé.
2. **Action** — avant d'exécuter une tâche, écrire la ligne dans `log.md`.
3. **Gate** — une vérification statique en échec **interdit** la synchronisation du ledger (compiler/linter au vert d'abord — ne jamais annoncer « check OK » sans l'avoir lancé).
4. **Synchronisation** — après chaque écriture ou test, mettre à jour le fichier de statut associé.
5. **Erreurs** — en cas d'exception ou d'interruption, l'état valide = dernière entrée du `log.md` + assertions de `progress.md`.

## §4 Git & livraison

- **Jamais de travail ni de push direct sur `main`** : branche `feat/…` ou `fix/…` avant toute modification.
- Une fois la PR soumise : **s'arrêter** (pas de boucle d'attente) ; merge uniquement sur instruction explicite.
- **Jamais `git reset --hard` sur un working tree vivant** — annulation d'un commit de test : `git reset --soft HEAD~1` puis purge ciblée.
- Push uniquement sur demande explicite de l'utilisateur.
- **Checklist avant commit** : tests/linters au vert · aucun secret dans le diff · doc maintenue à jour · ledger synchronisé.

## §5 Sécurité & intégrité

- **Aucun secret** dans le code, les commits, les logs ni l'écran (chemins utilisateur, e-mails, jetons) → env vars / figurants fictifs.
- **Jamais supprimer** les fichiers d'état, bases, archives ou données métier. Toute suppression ambiguë : **reformuler la liste** à l'utilisateur et faire confirmer AVANT d'exécuter.
- **Jamais éteindre/redémarrer/mettre en veille la machine** sans demande formelle explicite.
- **Actions irréversibles ou externes** (publication, upload, écriture PROD, envoi de messages) : générer d'abord les artefacts de contrôle, puis attendre l'accord explicite dans le chat.

## §6 Vérité & validation

- « Vérifié » = **exécuté réellement** (exit 0) ou **inspecté visuellement** (capture/rendu regardés) — jamais déduit du code, des intentions ou des logs.
- Toute affirmation factuelle (chiffre, couleur, présence d'un asset) est étayée par une mesure ou une capture conservée en preuve.
- Après une correction : re-valider par le **chemin complet réel**, pas par un harnais qui le court-circuite.
- Documentation : toute évolution de comportement → mettre à jour la doc maintenue du dépôt avant de clore la tâche.

<!-- END:agents-commun -->

---

## §7 Spécifique projet

### Mission / périmètre

Dépôt canonique de la **base commune AGENTS.md** : le bloc délimité dans `agents-commun.md`, le template d'instanciation et le script `scripts/sync_agents.py` (audit / check / sync / init) qui la distribue sur les dépôts voisins. Publication GitHub publique, licence MIT. Le kit ne contient **aucun chemin machine ni nom de dépôt spécifique** — le spécifique vit chez chaque dépôt consommateur.

### Emplacements déclarés (écarts au commun)

- Ledger : racine (non instancié dans ce dépôt — le kit n'a pas de sprint ; le créer seulement si une vraie suite de features démarre).
- Statuts / types de log : standard, pas d'extension.
- Shell : Git Bash. Encodage des fichiers du kit : **UTF-8 sans BOM, fins de ligne LF** (le script écrit `newline="\n"`).

### Commandes clés

```bash
# état de la flotte (défaut : dossier parent = C:\GIT)
uv run --no-project python scripts/sync_agents.py audit
# vérifier / resynchroniser un dépôt
uv run --no-project python scripts/sync_agents.py check ../<dépôt>
uv run --no-project python scripts/sync_agents.py sync  ../<dépôt>
# rafraîchir le template du kit après édition du canon
uv run --no-project python scripts/sync_agents.py sync . --fichier template/AGENTS.template.md
# instancier un nouveau dépôt
uv run --no-project python scripts/sync_agents.py init ../<nouveau> --nom "<Nom>" --ledger
```

### Invariants métier (à ne jamais casser)

- **`agents-commun.md` est l'unique source de vérité** du bloc ; `template/AGENTS.template.md` et le `AGENTS.md` du kit doivent contenir EXACTEMENT le même bloc (`check --fichier` le prouve). Après toute édition du canon : resynchroniser les deux avant de commit.
- **Version dans le marqueur** : toute évolution du contenu du bloc monte la version `BEGIN:agents-commun vX.Y` ; jamais d'édition silencieuse.
- **Marqueurs stricts** : une ligne `<!-- BEGIN:agents-commun … -->`, une ligne `<!-- END:agents-commun -->` — le script ne remplace qu'entre elles. Ne pas imbriquer d'autres marqueurs dans le bloc.
- **Zéro dépendance** pour le script (stdlib uniquement, Python 3.11+) ; aucune écriture hors des fichiers cibles ; l'`audit` ne modifie jamais rien.
- Le commun reste **générique** : aucune référence à un chemin, un utilisateur ou un dépôt particulier (ça vit au §7 des consommateurs).

### Pièges & leçons (format daté)

- **[2026-09-26] audit initial** — le socle « 4 fichiers » copié-collé avait dérivé en 8 variantes sur 11 dépôts, 3 fichiers corrompus par export riche (`\#`, `&#x20;`), 5 doublons octet-identiques : la dérive est la règle sans bloc géré, pas l'exception.

### Renvois

- Audit complet : `docs/audit-2026-09-26.md` — plan de migration : `docs/MIGRATION.md`.
