"""Graphes du rapport (voir notes/rapport.md). Figures écrites dans results/figures/ (PNG et PDF).

Usage :
    python src/graphes.py                                  graphes 1 à 8 depuis results/
    python src/graphes.py <instance.json> <solution.txt>   + graphes 9 à 11 pour cette solution
"""
import glob
import os
import sys

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

from campagne import INSTANCES_REGLAGE
from evaluation import Evaluation
from logger import RESULTS_DIR, instance_name, read_csv
from reader import read_instance, read_solution, duration

FIG_DIR = os.path.join(RESULTS_DIR, 'figures')

# --------------------------------------------------------------------- style
SURFACE = '#fcfcfb'
INK = '#0b0b0b'
INK_2 = '#52514e'
MUTED = '#898781'
GRID = '#e1e0d9'
BASELINE = '#c3c2b7'
# Palette catégorielle validée (ordre fixe) ; chaque méthode garde toujours sa couleur
CATEGORICAL = ['#2a78d6', '#eb6834', '#1baf7a', '#eda100', '#e87ba4', '#008300', '#4a3aa7', '#e34948']
METHODES = ['glouton', 'recuit', 'plne', 'grasp', 'recuit+descente', 'tabou']
SEASON_COLORS = {'winter': '#cde2fb', 'summer': '#fbe3d6', 'is': '#f0efec'}
SEASON_LABELS = {'winter': 'hiver', 'summer': 'été', 'is': 'intersaison'}

plt.rcParams.update({
    'figure.facecolor': SURFACE, 'axes.facecolor': SURFACE, 'savefig.facecolor': SURFACE,
    'font.family': 'sans-serif', 'font.size': 10,
    'text.color': INK, 'axes.labelcolor': INK_2, 'axes.titlecolor': INK,
    'axes.titlesize': 12, 'axes.titleweight': 'bold', 'axes.titlelocation': 'left',
    'axes.edgecolor': BASELINE, 'axes.spines.top': False, 'axes.spines.right': False,
    'axes.grid': True, 'axes.axisbelow': True, 'grid.color': GRID, 'grid.linewidth': 0.6,
    'xtick.color': MUTED, 'ytick.color': MUTED, 'xtick.labelcolor': INK_2, 'ytick.labelcolor': INK_2,
    'lines.linewidth': 2, 'legend.frameon': False, 'axes.prop_cycle': matplotlib.cycler(color=CATEGORICAL),
})


def couleur(methode: str) -> str:
    """Couleur fixe d'une méthode (ou d'une variante) : ne dépend pas des autres séries affichées."""
    if methode in METHODES:
        return CATEGORICAL[METHODES.index(methode)]
    return CATEGORICAL[(len(METHODES) + sum(map(ord, methode))) % len(CATEGORICAL)]


def sauver(fig, nom: str):
    os.makedirs(FIG_DIR, exist_ok=True)
    fig.tight_layout()
    # Sans date de création dans le PDF : une figure inchangée ne crée pas de diff git
    fig.savefig(os.path.join(FIG_DIR, f'{nom}.png'), dpi=200)
    fig.savefig(os.path.join(FIG_DIR, f'{nom}.pdf'), metadata={'CreationDate': None})
    plt.close(fig)
    print(f'  {nom}')


# ------------------------------------------------------------ données utiles

def meilleurs_par(rows: list, cle: str) -> dict:
    """{instance: {valeur de `cle`: meilleur objectif réalisable}}."""
    best = {}
    for r in rows:
        if r['realisable'] != 1:
            continue
        d = best.setdefault(r['instance'], {})
        k = str(r[cle])
        d[k] = min(d.get(k, np.inf), r['objectif'])
    return best


def references(rows: list) -> dict:
    """Référence par instance : meilleure solution connue (results/best_known.csv), sinon meilleure trouvée."""
    ref = {}
    for r in rows:
        if r['realisable'] == 1:
            ref[r['instance']] = min(ref.get(r['instance'], np.inf), r['objectif'])
    for r in read_csv(os.path.join(RESULTS_DIR, 'best_known.csv')):
        ref[r['instance']] = r['objectif']
    return ref


def ecart(obj: float, ref: float) -> float:
    return 100.0 * (obj - ref) / ref if ref else 0.0


def etiquettes(ax, instances: list):
    """Noms d'instances en abscisse ; * sur celles qui ont servi au réglage du recuit."""
    if any(i in INSTANCES_REGLAGE for i in instances):
        ax.annotate('* instance de réglage des paramètres', (1, 1), xycoords='axes fraction',
                    ha='right', va='bottom', fontsize=8, color=MUTED)
    return [f'{i}*' if i in INSTANCES_REGLAGE else i for i in instances]


# ------------------------------------------------------- comparer méthodes

def barres_ecart(rows: list, nom: str, titre: str, cle: str = 'methode', ordre: list = None):
    """Graphes 1, 7 et 8 : barres groupées de l'écart (%) à la référence, par instance."""
    best = meilleurs_par(rows, cle)
    if not best:
        return
    ref = references(rows)
    instances = sorted(best)
    series = ordre or sorted({k for d in best.values() for k in d})
    series = [s for s in series if any(s in best[i] for i in instances)]
    largeur = 0.8 / len(series)
    # Méthodes : couleur fixe par méthode ; autres clés (variantes) : slots dans l'ordre trié
    couleurs = {sr: couleur(sr) if cle == 'methode' else CATEGORICAL[k % len(CATEGORICAL)]
                for k, sr in enumerate(series)}
    fig, ax = plt.subplots(figsize=(min(12, max(6, 0.45 * len(instances) * len(series))), 4))
    x = np.arange(len(instances))
    for k, sr in enumerate(series):
        xs = x + (k - (len(series) - 1) / 2) * largeur
        vals = [ecart(best[i][sr], ref[i]) if sr in best[i] else np.nan for i in instances]
        ax.bar(xs, vals, width=largeur * 0.9, color=couleurs[sr], label=sr, edgecolor=SURFACE, linewidth=1)
        # Une barre à 0 % est invisible : marquer la série de référence
        for xi, v in zip(xs, vals):
            if v == 0:
                ax.annotate('réf.', (xi, 0), xytext=(0, 3), textcoords='offset points',
                            ha='center', va='bottom', fontsize=7, color=INK_2)
    noms = etiquettes(ax, instances) if cle == 'methode' else instances
    ax.set_xticks(x, noms, rotation=45 if len(instances) > 8 else 0)
    ax.set_ylabel('écart à la référence (%)')
    ax.set_title(titre)
    ax.grid(axis='x', visible=False)
    if len(series) > 1:
        ax.legend(ncols=len(series), loc='upper left', bbox_to_anchor=(0, -0.15 if len(instances) <= 8 else -0.25))
    sauver(fig, nom)


def boites_graines(rows: list, methode: str = 'recuit+descente'):
    """Graphe 2 : dispersion de l'objectif sur plusieurs graines, par instance."""
    par_instance = {}
    for r in rows:
        if r['methode'] == methode and r['realisable'] == 1:
            par_instance.setdefault(r['instance'], []).append(r['objectif'])
    par_instance = {i: v for i, v in par_instance.items() if len(v) > 1}
    if not par_instance:
        return
    ref = references(rows)
    instances = sorted(par_instance)
    data = [[ecart(v, ref[i]) for v in par_instance[i]] for i in instances]
    fig, ax = plt.subplots(figsize=(max(6, 0.7 * len(instances)), 4))
    ax.boxplot(data, tick_labels=etiquettes(ax, instances), widths=0.5, patch_artist=True,
               boxprops=dict(facecolor=couleur(methode), edgecolor=couleur(methode), alpha=0.35),
               medianprops=dict(color=couleur(methode), linewidth=2),
               whiskerprops=dict(color=MUTED), capprops=dict(color=MUTED),
               flierprops=dict(marker='o', markersize=4, markeredgecolor=MUTED))
    ax.set_ylabel('écart à la référence (%)')
    ax.set_title(f'Dispersion du {methode} sur plusieurs graines')
    ax.grid(axis='x', visible=False)
    sauver(fig, f'2_dispersion_{methode.replace("+", "_")}')


def qualite_temps(rows: list):
    """Graphe 3 : écart à la référence selon le temps de calcul, une couleur par méthode."""
    ref = references(rows)
    rows = [r for r in rows if r['realisable'] == 1]
    if not rows:
        return
    fig, ax = plt.subplots(figsize=(6, 4))
    for m in [m for m in METHODES if any(r['methode'] == m for r in rows)]:
        pts = [(r['temps'], ecart(r['objectif'], ref[r['instance']])) for r in rows if r['methode'] == m]
        ax.scatter(*zip(*pts), s=64, color=couleur(m), label=m, edgecolors=SURFACE, linewidths=1.5)
    ax.set_xscale('log')
    ax.set_xlabel('temps de calcul (s, échelle log)')
    ax.set_ylabel('écart à la référence (%)')
    ax.set_title('Qualité selon le temps de calcul')
    ax.legend()
    sauver(fig, '3_qualite_temps')


# --------------------------------------------------------- comportement du recuit

def convergence(fichiers: list):
    """Graphe 4 : coût courant et meilleur coût en fonction du temps (une case par exécution)."""
    fichiers = fichiers[:4]
    if not fichiers:
        return
    fig, axes = plt.subplots(1, len(fichiers), figsize=(4.5 * len(fichiers), 3.6), squeeze=False)
    for ax, f in zip(axes[0], fichiers):
        rows = read_csv(f)
        t = [r['temps'] for r in rows]
        ax.plot(t, [r['cout_courant'] for r in rows], color=BASELINE, linewidth=1, label='coût courant')
        ax.plot(t, [r['meilleur_cout'] for r in rows], color=CATEGORICAL[0], label='meilleur coût')
        ax.set_title(os.path.splitext(os.path.basename(f))[0], fontsize=10)
        ax.set_xlabel('temps (s)')
    axes[0][0].set_ylabel('coût pénalisé')
    axes[0][0].legend()
    fig.suptitle('Convergence du recuit', x=0.01, ha='left', fontweight='bold')
    sauver(fig, '4_convergence')


def temperature_acceptation(fichier: str):
    """Graphe 5 : température et taux d'acceptation (deux graphes empilés, pas de double axe)."""
    rows = read_csv(fichier)
    if not rows:
        return
    it = [r['iteration'] for r in rows]
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(6, 5), sharex=True)
    ax1.plot(it, [r['temperature'] for r in rows], color=CATEGORICAL[0])
    ax1.set_ylabel('température')
    ax1.set_title(f'Température et acceptation — {os.path.splitext(os.path.basename(fichier))[0]}')
    ax2.plot(it, [100 * r['taux_acceptation'] for r in rows], color=CATEGORICAL[1])
    ax2.set_ylabel('acceptation (%)')
    ax2.set_ylim(0, 100)
    ax2.set_xlabel('itération')
    sauver(fig, '5_temperature_acceptation')


def mouvements(fichiers: list):
    """Graphe 6 : part des déplacements et des swaps parmi les mouvements acceptés.
    Une barre par instance et par variante : les graines sont cumulées."""
    cumul = {}
    for f in fichiers:
        rows = read_csv(f)
        if rows:
            nom = os.path.splitext(os.path.basename(f))[0].rsplit('_s', 1)[0].replace('_recuit', '')
            d, s = cumul.get(nom, (0, 0))
            cumul[nom] = (d + rows[-1]['deplacements_acceptes'], s + rows[-1]['swaps_acceptes'])
    cumul = {n: v for n, v in sorted(cumul.items()) if sum(v)}
    if not cumul:
        return
    noms = list(cumul)
    dep = [100 * d / (d + s) for d, s in cumul.values()]
    swp = [100 * s / (d + s) for d, s in cumul.values()]
    fig, ax = plt.subplots(figsize=(max(6, 0.7 * len(noms)), 4))
    x = np.arange(len(noms))
    ax.bar(x, dep, width=0.6, color=CATEGORICAL[0], label='déplacements', edgecolor=SURFACE, linewidth=1)
    ax.bar(x, swp, width=0.6, bottom=dep, color=CATEGORICAL[1], label='swaps', edgecolor=SURFACE, linewidth=1)
    ax.set_xticks(x, noms, rotation=45, ha='right')
    ax.set_ylabel('mouvements acceptés (%)')
    ax.set_ylim(0, 100)
    ax.grid(axis='x', visible=False)
    ax.legend(ncols=2, loc='lower left', bbox_to_anchor=(0, 1.0))
    ax.set_title('Répartition des mouvements acceptés', pad=26)
    sauver(fig, '6_mouvements')


# -------------------------------------------------------- illustrer une solution

def evaluation_solution(instance: dict, starts: dict) -> Evaluation:
    ev = Evaluation(instance)
    for i, s in starts.items():
        ev.assign({i: s})
    return ev


def bandes_saisons(ax, instance: dict, avec_legende: bool = True):
    for season, periods in instance['Seasons'].items():
        for k, t in enumerate(sorted(int(p) for p in periods)):
            ax.axvspan(t - 0.5, t + 0.5, color=SEASON_COLORS.get(season, GRID), linewidth=0,
                       zorder=0, label=SEASON_LABELS.get(season, season) if avec_legende and k == 0 else None)


def gantt(instance: dict, starts: dict, nom: str):
    """Graphe 9 : une barre par intervention, saisons en fond."""
    items = sorted(starts.items(), key=lambda x: x[1])
    fig, ax = plt.subplots(figsize=(8, max(4, 0.03 * len(items) + 2)))
    bandes_saisons(ax, instance)
    for y, (i, s) in enumerate(items):
        ax.barh(y, duration(instance['Interventions'][i], s), left=s - 0.5, height=0.8,
                color=CATEGORICAL[0], linewidth=0)
    ax.set_ylim(len(items), -1)
    ax.set_yticks([])
    ax.set_xlim(0.5, instance['T'] + 0.5)
    ax.set_xlabel('période')
    ax.set_ylabel(f'{len(items)} interventions (triées par date de début)')
    ax.set_title(f'Planning — {nom}')
    ax.grid(axis='y', visible=False)
    ax.legend(ncols=3, loc='upper left', bbox_to_anchor=(0, -0.08))
    sauver(fig, f'9_gantt_{nom}')


def ressources(instance: dict, ev: Evaluation, nom: str, n_max: int = 4):
    """Graphe 10 : charge des ressources les plus tendues entre leurs bornes min et max."""
    noms = list(ev.res_index)
    tension = [(ev.usage[k] / np.maximum(ev.r_max[k], 1e-9)).max() for k in range(len(noms))]
    choix = sorted(range(len(noms)), key=lambda k: -tension[k])[:n_max]
    t = np.arange(1, ev.T + 1)
    fig, axes = plt.subplots(len(choix), 1, figsize=(8, 2.2 * len(choix)), sharex=True, squeeze=False)
    for ax, k in zip(axes[:, 0], choix):
        ax.fill_between(t, ev.r_min[k], ev.r_max[k], step='mid', color=GRID, linewidth=0, label='bornes [min, max]')
        ax.step(t, ev.usage[k], where='mid', color=CATEGORICAL[0], label='charge')
        ax.set_ylabel(noms[k], fontsize=9)
    axes[0, 0].set_title(f'Charge des ressources les plus tendues — {nom}', pad=26)
    axes[0, 0].legend(ncols=2, loc='lower left', bbox_to_anchor=(0, 1.0), fontsize=9)
    axes[-1, 0].set_xlabel('période')
    sauver(fig, f'10_ressources_{nom}')


def risque(ev: Evaluation, nom: str, quantile: float):
    """Graphe 11 : risque moyen et quantile par période ; l'écart est le terme d'excès."""
    means = np.array([r.mean() for r in ev.risk])
    q = np.array([np.partition(r, k)[k] for r, k in zip(ev.risk, ev.q_idx)])
    t = np.arange(1, ev.T + 1)
    fig, ax = plt.subplots(figsize=(8, 3.6))
    ax.fill_between(t, means, np.maximum(q, means), color=CATEGORICAL[1], alpha=0.2, linewidth=0,
                    label='excès (quantile − moyenne)')
    ax.plot(t, q, color=CATEGORICAL[1], label=f'quantile {quantile:g}')
    # Tracé après le quantile : reste visible quand les deux courbes sont confondues (1 scénario)
    ax.plot(t, means, color=CATEGORICAL[0], linewidth=1.5, label='risque moyen')
    ax.set_xlabel('période')
    ax.set_ylabel('risque')
    ax.legend(ncols=3, loc='lower left', bbox_to_anchor=(0, 1.0), fontsize=9)
    ax.set_title(f'Risque par période — {nom}', pad=28)
    sauver(fig, f'11_risque_{nom}')


# ---------------------------------------------------------------------- main

def main():
    rows = read_csv(os.path.join(RESULTS_DIR, 'results.csv'))
    conv = sorted(glob.glob(os.path.join(RESULTS_DIR, 'convergence', '*.csv')))
    print(f'Figures dans {FIG_DIR} :')
    barres_ecart(rows, '1_methodes', 'Écart à la référence par méthode', ordre=METHODES)
    boites_graines(rows)
    qualite_temps(rows)
    convergence(conv)
    if conv:
        temperature_acceptation(conv[0])
    mouvements(conv)
    barres_ecart([r for r in rows if r['methode'] == 'glouton'], '7_criteres_tri',
                 'Critères de tri du glouton', cle='variante')
    barres_ecart([r for r in rows if r['methode'] in ('glouton', 'recuit', 'recuit+descente')],
                 '8_apport_etapes', 'Apport de chaque étape', ordre=['glouton', 'recuit', 'recuit+descente'])

    if len(sys.argv) == 3:
        instance = read_instance(sys.argv[1])
        nom = instance_name(sys.argv[1])
        starts = read_solution(sys.argv[2])
        ev = evaluation_solution(instance, starts)
        gantt(instance, starts, nom)
        ressources(instance, ev, nom)
        risque(ev, nom, instance['Quantile'])
    elif len(sys.argv) != 1:
        sys.exit('Usage : python src/graphes.py [<instance.json> <solution.txt>]')


if __name__ == '__main__':
    main()
