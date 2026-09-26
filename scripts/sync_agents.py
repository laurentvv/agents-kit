#!/usr/bin/env python3
"""agents-kit — gestion du bloc commun AGENTS.md.

Le bloc commun est délimité par les marqueurs HTML
``<!-- BEGIN:agents-commun ... -->`` / ``<!-- END:agents-commun -->``
(même mécanisme que les blocs gérés Next.js ou OpenSpec) : le script
remplace uniquement ce qui se trouve ENTRE les marqueurs et préserve
tout le contenu spécifique du dépôt.

Commandes
---------
  audit [racine]            État de tous les <racine>/<dépôt>/AGENTS.md
                             (défaut : le dossier parent d'agents-kit).
  check <dépôt>             Le bloc commun est-il identique au canonique ?
  sync  <dépôt>             Resynchronise le bloc commun depuis agents-commun.md.
  init  <dépôt> [--nom N]   Crée AGENTS.md depuis le template.
                             --force : écraser un fichier existant.
                             --ledger : crée aussi les 4 fichiers d'état manquants.

Option --fichier <chemin> (check/sync) : cibler un autre fichier que AGENTS.md
à la racine du dépôt (ex. ``template/AGENTS.template.md`` pour le kit lui-même).

Zéro dépendance externe — Python 3.11+ (stdlib uniquement).
Codes retour : 0 = ok · 1 = dérive détectée · 2 = erreur d'entrée.
"""
from __future__ import annotations

import argparse
import re
import sys
from datetime import date
from pathlib import Path

KIT = Path(__file__).resolve().parent.parent  # racine du dépôt agents-kit
CANONIQUE = KIT / "agents-commun.md"
TEMPLATE = KIT / "template" / "AGENTS.template.md"

BEGIN_RE = re.compile(r"<!--\s*BEGIN:agents-commun")
END_RE = re.compile(r"<!--\s*END:agents-commun")
VERSION_RE = re.compile(r"BEGIN:agents-commun\s+(v[0-9][0-9.]*)")
CORRUPTION_RE = re.compile(r"^\\[#\*]|^\\\*|&#x20;", re.MULTILINE)
MARQUEURS_GENERES = ("OPENSPEC:START", "nextjs-agent-rules", "NEXT-AGENTS-MD-START")


# ---------------------------------------------------------------- utilitaires

def lire(p: Path) -> str:
    return p.read_text(encoding="utf-8").replace("\r\n", "\n")


def ecrire(p: Path, texte: str) -> None:
    p.write_text(texte, encoding="utf-8", newline="\n")


def bornes_bloc(lignes: list[str]) -> tuple[int, int] | None:
    """Indices [debut, fin] INCLUS des lignes de marqueurs BEGIN/END."""
    debut = fin = None
    for i, ligne in enumerate(lignes):
        if BEGIN_RE.search(ligne):
            debut = i
        elif END_RE.search(ligne) and debut is not None:
            fin = i
            break
    if debut is None or fin is None:
        return None
    return debut, fin


def extraire_bloc(texte: str) -> str:
    bornes = bornes_bloc(texte.split("\n"))
    if bornes is None:
        return ""
    lignes = texte.split("\n")
    return "\n".join(lignes[bornes[0] : bornes[1] + 1]).strip("\n")


def bloc_canonique() -> str:
    return lire(CANONIQUE).strip("\n")


def version_du(bloc: str) -> str:
    m = VERSION_RE.search(bloc)
    return m.group(1) if m else "version inconnue"


# ------------------------------------------------------------------ commandes

def cmd_audit(racine: Path) -> int:
    print(f"Audit des AGENTS.md sous : {racine}\n")
    stats: dict[str, int] = {}
    for d in sorted(racine.iterdir()):
        cible = d / "AGENTS.md"
        if not (d.is_dir() and cible.is_file()):
            continue
        etat = classifier(lire(cible))
        stats[etat] = stats.get(etat, 0) + 1
        print(f"  {etat:<42} {cible}")
    bilan = " · ".join(f"{v} {k}" for k, v in sorted(stats.items()))
    print(f"\nBilan : {bilan or 'aucun fichier trouvé'}")
    return 0


def classifier(texte: str) -> str:
    if BEGIN_RE.search(texte) and END_RE.search(texte):
        return "à jour" if extraire_bloc(texte) == bloc_canonique() else "dérivé du canonique"
    if any(m in texte for m in MARQUEURS_GENERES):
        return "généré (OpenSpec/Next.js — ne pas gérer)"
    if CORRUPTION_RE.search(texte):
        return "corrompu (markdown échappé) — à réécrire"
    return "non géré (à migrer)"


def cmd_check(repo: Path, fichier: str) -> int:
    cible = repo / fichier
    if not cible.is_file():
        print(f"ABSENT   : {cible}")
        return 2
    texte = lire(cible)
    if bornes_bloc(texte.split("\n")) is None:
        print(f"NON GÉRÉ : {cible} (aucun marqueur agents-commun)")
        return 2
    actuel = extraire_bloc(texte)
    canon = bloc_canonique()
    if actuel == canon:
        print(f"À JOUR   : {cible} ({version_du(canon)})")
        return 0
    print(f"DÉRIVÉ    : {cible}")
    print(f"  bloc installé  : {version_du(actuel)}")
    print(f"  bloc canonique : {version_du(canon)}")
    return 1


def cmd_sync(repo: Path, fichier: str) -> int:
    cible = repo / fichier
    if not cible.is_file():
        print(f"ABSENT   : {cible} — utiliser 'init' pour créer le fichier.")
        return 2
    lignes = lire(cible).split("\n")
    bornes = bornes_bloc(lignes)
    if bornes is None:
        print(f"NON GÉRÉ : {cible} — aucun marqueur. Migrer à la main ou 'init --force'.")
        return 2
    canon = bloc_canonique()
    nouveau = lignes[: bornes[0]] + canon.split("\n") + lignes[bornes[1] + 1 :]
    ecrire(cible, "\n".join(nouveau))
    print(f"Resynchronisé : {cible} ({version_du(canon)})")
    return 0


def cmd_init(repo: Path, nom: str | None, force: bool, ledger: bool) -> int:
    cible = repo / "AGENTS.md"
    if cible.exists() and not force:
        print(f"EXISTE DÉJÀ : {cible} (utiliser --force pour écraser)")
        return 2
    nom = nom or repo.name
    ecrire(cible, lire(TEMPLATE).replace("<NOM DU DÉPÔT>", nom))
    print(f"Créé : {cible}")
    if ledger:
        creer_ledger(repo)
    return 0


def creer_ledger(repo: Path) -> None:
    if not (repo / "feature_list.json").exists():
        ecrire(repo / "feature_list.json", '{\n  "features": []\n}\n')
        print("Créé : feature_list.json")
    if not (repo / "progress.md").exists():
        ecrire(
            repo / "progress.md",
            "# État d'Avancement du Sprint\n\n"
            "## Objectif Actuel\n- [ ] …\n\n"
            "## Jalons de l'Itération\n- [ ] …\n",
        )
        print("Créé : progress.md")
    if not (repo / "contract.md").exists():
        ecrire(
            repo / "contract.md",
            "# Contrat de Validation\n\n"
            "## Critères d'Acceptation Automatisés\n- [ ] Critère 1 : …\n\n"
            "## Protocole d'Évaluation\n"
            "* Commande d'exécution des tests : `pytest` / `npm test`\n"
            "* Comportement attendu : zéro avertissement, zéro échec.\n",
        )
        print("Créé : contract.md")
    if not (repo / "log.md").exists():
        ecrire(
            repo / "log.md",
            "# Journal d'Exécution (Append-Only)\n\n"
            f"## [{date.today().isoformat()}] init | Instanciation agents-kit (template AGENTS.md).\n",
        )
        print("Créé : log.md")


# ------------------------------------------------------------------------ main

def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="agents-kit — bloc commun AGENTS.md")
    sub = ap.add_subparsers(dest="cmd", required=True)

    a = sub.add_parser("audit", help="état de tous les AGENTS.md sous <racine>")
    a.add_argument("racine", nargs="?", type=Path, default=KIT.parent)

    for nom, aide in (("check", "le bloc commun est-il à jour ?"), ("sync", "resynchroniser le bloc commun")):
        s = sub.add_parser(nom, help=aide)
        s.add_argument("repo", type=Path)
        s.add_argument("--fichier", default="AGENTS.md", help="cible alternative (défaut : AGENTS.md)")

    i = sub.add_parser("init", help="créer AGENTS.md depuis le template")
    i.add_argument("repo", type=Path)
    i.add_argument("--nom", help="nom affiché du dépôt (défaut : nom du dossier)")
    i.add_argument("--force", action="store_true", help="écraser un AGENTS.md existant")
    i.add_argument("--ledger", action="store_true", help="créer aussi les 4 fichiers d'état manquants")

    args = ap.parse_args(argv)
    if args.cmd == "audit":
        if not args.racine.is_dir():
            print(f"Racine introuvable : {args.racine}")
            return 2
        return cmd_audit(args.racine)
    if args.cmd == "check":
        return cmd_check(args.repo.resolve(), args.fichier)
    if args.cmd == "sync":
        return cmd_sync(args.repo.resolve(), args.fichier)
    return cmd_init(args.repo.resolve(), args.nom, args.force, args.ledger)


if __name__ == "__main__":
    sys.exit(main())
