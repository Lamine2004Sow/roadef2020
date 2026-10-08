"""Tableau comparatif glouton / recuit / PLNE au temps du challenge (voir notes/rapport.md).

Usage : python src/tableau.py
Lit results/results.csv et results/best_known.csv ; écrit results/tableau.csv, results/tableau.md
et results/tableau.tex (inclus dans rapport/main.tex).
Une ligne par instance A, en deux blocs : instances hors réglage, puis instances de réglage du recuit.
    glouton : exécution la plus récente
    recuit  : recuit+descente de la campagne finale (graines, sans variante), moyenne ± écart-type et meilleure
    PLNE    : exécution la plus récente de chaque variante (modèle seul, avec coupes de quantile) ;
              meilleure solution et meilleure borne des variantes, toutes deux certifiées, d'où le gap
"""
import csv
import os
import statistics

from campagne import INSTANCES_REGLAGE
from logger import RESULTS_DIR, read_csv

COLONNES = ['instance', 'reglage', 'reference', 'glouton', 'temps_glouton',
            'recuit_moyenne', 'recuit_ecart_type', 'recuit_meilleur', 'recuit_pire', 'recuit_realisables', 'recuit_graines',
            'plne', 'plne_borne', 'plne_gap', 'temps_plne', 'plne_coupes',
            'ecart_glouton', 'ecart_recuit_moyenne', 'ecart_recuit_meilleur', 'ecart_recuit_pire', 'ecart_plne']


def ecart(obj, ref):
    return None if obj is None else 100.0 * (obj - ref) / ref


def lignes() -> list:
    rows = read_csv(os.path.join(RESULTS_DIR, 'results.csv'))
    ref = {r['instance']: r['objectif'] for r in read_csv(os.path.join(RESULTS_DIR, 'best_known.csv'))}
    dernier = {}  # (instance, méthode) -> exécution la plus récente (results.csv est chronologique)
    recuit = {}
    for r in rows:
        if r['methode'] == 'glouton':
            dernier[r['instance'], r['methode']] = r
        elif r['methode'] == 'plne':
            dernier[r['instance'], 'plne', r['variante'] or ''] = r
        elif r['methode'] == 'recuit+descente' and r['graine'] != '' and not r['variante']:
            recuit.setdefault(r['instance'], []).append(r)
    out = []
    for inst in sorted(ref):
        g = dernier.get((inst, 'glouton'))
        variantes = [r for (i, m, *_), r in dernier.items() if i == inst and m == 'plne']
        ok_p = [r for r in variantes if r['realisable'] == 1]
        p_sol = min(ok_p, key=lambda r: r['objectif']) if ok_p else None
        p_borne = max(variantes, key=lambda r: r['borne']) if variantes else None
        rec = recuit.get(inst, [])
        ok = [r['objectif'] for r in rec if r['realisable'] == 1]
        l = {'instance': inst, 'reglage': int(inst in INSTANCES_REGLAGE), 'reference': ref[inst],
             'glouton': g['objectif'] if g and g['realisable'] == 1 else None,
             'temps_glouton': g['temps'] if g else None,
             'recuit_moyenne': statistics.mean(ok) if ok else None,
             'recuit_ecart_type': statistics.stdev(ok) if len(ok) > 1 else (0.0 if ok else None),
             'recuit_meilleur': min(ok) if ok else None, 'recuit_pire': max(ok) if ok else None,
             'recuit_realisables': len(ok), 'recuit_graines': len(rec),
             'plne': p_sol['objectif'] if p_sol else None,
             'plne_borne': p_borne['borne'] if p_borne else None,
             'plne_gap': None if not (p_sol and p_borne) else
             0.0 if min(r['gap'] for r in variantes) < 1e-9 else
             max(0.0, 100 * (p_sol['objectif'] - p_borne['borne']) / abs(p_sol['objectif'])),
             'temps_plne': p_borne['temps'] if p_borne else None,
             'plne_coupes': int(bool(p_borne) and p_borne['variante'] == 'coupes')}
        for k in ('glouton', 'recuit_moyenne', 'recuit_meilleur', 'recuit_pire', 'plne'):
            l[f'ecart_{k}'] = ecart(l[k], ref[inst])
        out.append(l)
    return out


# ------------------------------------------------------------------ markdown

def nombre(x, d=2) -> str:
    return '–' if x is None else f'{x:.{d}f}'.replace('.', ',')


def pourcent(x) -> str:
    """Écart (%) : 0 sous 0,001 %, 3 décimales sous 0,01 %, sinon 2."""
    if x is None:
        return '–'
    if abs(x) < 1e-3:
        return '0'
    return f'{nombre(x, 3 if abs(x) < 0.01 else 2)} %'


def avec_ecart(obj, e) -> str:
    if obj is None:
        return '–'
    cell = f'{nombre(obj)} ({pourcent(e)})'
    return f'**{cell}**' if abs(e) < 1e-3 else cell


def temps(s) -> str:
    return '–' if s is None else f'{s:.0f} s' if s >= 10 else f'{nombre(s, 1)} s'


def gap(l) -> str:
    if l['plne_gap'] is None:
        return '–'
    return '0 (optimal)' if l['plne_gap'] < 1e-6 else pourcent(l['plne_gap'])


def moyenne(ls: list, cle: str) -> str:
    """Moyenne des écarts disponibles ; précise sur combien d'instances si certaines manquent."""
    v = [l[cle] for l in ls if l[cle] is not None]
    if not v:
        return '–'
    return pourcent(statistics.mean(v)) + ('' if len(v) == len(ls) else f' ({len(v)}/{len(ls)})')


def bloc(titre: str, ls: list) -> list:
    md = [f'**{titre} ({len(ls)})**', '',
          '| Instance | Référence | Glouton | Recuit : moyenne ± σ | Recuit : meilleur | PLNE | Borne PLNE '
          '| Gap certifié | Temps glouton | Temps PLNE |',
          '|---|---|---|---|---|---|---|---|---|---|']
    for l in ls:
        moy = '–' if l['recuit_moyenne'] is None else (
            f'{nombre(l["recuit_moyenne"])} ± {nombre(l["recuit_ecart_type"])} ({pourcent(l["ecart_recuit_moyenne"])})')
        md.append(f'| {l["instance"]} | {nombre(l["reference"])} '
                  f'| {avec_ecart(l["glouton"], l["ecart_glouton"])} | {moy} '
                  f'| {avec_ecart(l["recuit_meilleur"], l["ecart_recuit_meilleur"])} '
                  f'| {avec_ecart(l["plne"], l["ecart_plne"])} | {nombre(l["plne_borne"])}{" †" if l["plne_coupes"] else ""} '
                  f'| {gap(l)} '
                  f'| {temps(l["temps_glouton"])} | {temps(l["temps_plne"])} |')
    md.append(f'| **Moyenne** | | {moyenne(ls, "ecart_glouton")} | {moyenne(ls, "ecart_recuit_moyenne")} '
              f'| {moyenne(ls, "ecart_recuit_meilleur")} | {moyenne(ls, "ecart_plne")} | '
              f'| {moyenne(ls, "plne_gap")} | | |')
    return md + ['']


def markdown(ls: list) -> str:
    test = [l for l in ls if not l['reglage']]
    reglage = [l for l in ls if l['reglage']]
    real = sum(l['recuit_realisables'] for l in ls)
    graines = sum(l['recuit_graines'] for l in ls)
    optimales = [l['instance'] for l in ls if l['plne_gap'] is not None and l['plne_gap'] < 1e-6]
    md = ['<!-- Généré par python src/tableau.py : ne pas modifier à la main -->', '',
          'Écart (%) à la référence (meilleure valeur de la qualification du challenge) entre parenthèses ; '
          'en gras : référence atteinte (écart < 0,001 %). Gap certifié : (PLNE − borne) / PLNE, '
          'calculé par Gurobi ; † : borne obtenue avec les coupes de quantile (`--coupes`, voir `notes/plne.md`). '
          'Recuit et PLNE : `ComputationTime` du challenge (15 min) ; temps PLNE : celui de la meilleure borne.', '']
    md += bloc('Instances hors réglage', test)
    md += bloc('Instances de réglage du recuit', reglage)
    md += [f'- Recuit : {real}/{graines} exécutions réalisables (checker officiel).',
           f'- PLNE : optimum prouvé sur {len(optimales)} instance(s) ({", ".join(optimales) or "aucune"}).']
    return '\n'.join(md) + '\n'


# --------------------------------------------------------------------- LaTeX

def tex_cellule(obj, e) -> str:
    """Valeur et écart à la référence sur deux lignes ; en gras si la référence est atteinte."""
    if obj is None:
        return '--'
    val, ec = nombre(obj), pourcent(e).replace('%', r'\%')
    if abs(e) < 1e-3:
        val = rf'\textbf{{{val}}}'
    return rf'\makecell{{{val}\\ \footnotesize({ec})}}'


def tex_bloc(titre: str, ls: list) -> list:
    tex = [rf'\multicolumn{{8}}{{l}}{{\textit{{{titre} ({len(ls)})}}}} \\', r'\midrule']
    for l in ls:
        moy = '--' if l['recuit_moyenne'] is None else (
            rf'\makecell{{{nombre(l["recuit_moyenne"])} $\pm$ {nombre(l["recuit_ecart_type"])}\\ '
            rf'\footnotesize({pourcent(l["ecart_recuit_moyenne"])})}}'.replace('%', r'\%'))
        borne = nombre(l['plne_borne']) + (r'$^\dagger$' if l['plne_coupes'] else '')
        tex.append(' & '.join([l['instance'].replace('_', r'\_'), nombre(l['reference']),
                               tex_cellule(l['glouton'], l['ecart_glouton']), moy,
                               tex_cellule(l['recuit_meilleur'], l['ecart_recuit_meilleur']),
                               tex_cellule(l['plne'], l['ecart_plne']), borne,
                               gap(l).replace('%', r'\%')]) + r' \\')
    tex.append(' & '.join([r'\textbf{Moyenne}', '', moyenne(ls, 'ecart_glouton'), moyenne(ls, 'ecart_recuit_moyenne'),
                           moyenne(ls, 'ecart_recuit_meilleur'), moyenne(ls, 'ecart_plne'), '',
                           moyenne(ls, 'plne_gap')]).replace('%', r'\%') + r' \\')
    return tex


def latex(ls: list) -> str:
    """Corps du tableau (tabular) ; légende et environnement table dans le rapport."""
    tex = ['% Généré par python src/tableau.py : ne pas modifier à la main',
           r'\begin{tabular}{lrrrrrrr}', r'\toprule',
           r'Instance & Référence & Glouton & \makecell{Recuit\\ moy. $\pm$ $\sigma$} & \makecell{Recuit\\ meilleur} '
           r'& PLNE & \makecell{Borne\\ PLNE} & \makecell{Gap\\ certifié} \\', r'\midrule']
    tex += tex_bloc('Instances hors réglage', [l for l in ls if not l['reglage']])
    tex += [r'\midrule']
    tex += tex_bloc('Instances de réglage du recuit', [l for l in ls if l['reglage']])
    tex += [r'\bottomrule', r'\end{tabular}']
    return '\n'.join(tex) + '\n'


def main():
    ls = lignes()
    with open(os.path.join(RESULTS_DIR, 'tableau.csv'), 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=COLONNES)
        w.writeheader()
        w.writerows({k: '' if v is None else v for k, v in l.items()} for l in ls)
    md = markdown(ls)
    with open(os.path.join(RESULTS_DIR, 'tableau.md'), 'w') as f:
        f.write(md)
    with open(os.path.join(RESULTS_DIR, 'tableau.tex'), 'w') as f:
        f.write(latex(ls))
    print(md)


if __name__ == '__main__':
    main()
