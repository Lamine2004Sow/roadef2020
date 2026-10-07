# Pseudo-code du recuit simulé (LaTeX)

Code destiné au rapport : mêmes préambule et notations que `pseudocode_heuristique.md`
(à inclure une seule fois dans le rapport).
Correspondance avec le code : `src/meta_heuristique.py` (à écrire), `src/evaluation.py`, `src/logger.py`.

## Notations supplémentaires

```latex
\begin{itemize}
  \item $C(x) = \mathrm{obj}(x) + \lambda \, V(x)$ : coût pénalisé (voir le glouton).
  \item Ordre entre solutions : $x$ est \emph{meilleure} que $y$, noté $x \prec y$, si
        $V(x) < V(y)$, ou si $V(x) = V(y)$ et $\mathrm{obj}(x) < \mathrm{obj}(y)$
        (à la tolérance $\varepsilon = 10^{-5}$ près sur $V$).
        La meilleure solution ne dépend donc pas de $\lambda$, qui varie pendant le recuit.
  \item $\mathcal{S}_i = \{1, \dots, \min(t^{\max}_i, T)\}$ : dates de début possibles de $i$.
  \item $\mathcal{U}(E)$ : tirage uniforme dans l'ensemble $E$ ; $u \sim \mathcal{U}([0, 1])$.
  \item Paramètres : $p_{\mathrm{swap}}$ probabilité d'un swap, $p_{\mathrm{loc}}$ probabilité d'un
        déplacement local, $r$ rayon local, $L$ itérations par palier, $\alpha$ refroidissement,
        $\gamma$ croissance de $\lambda$, $p_0$ taux d'acceptation initial visé.
\end{itemize}
```

## Algorithme 5 : tirage d'un voisin (`voisin`)

```latex
\begin{algorithm}[H]
\caption{\textsc{Voisin}$(x)$}
\begin{algorithmic}[1]
\Require affectation complète $x$
\Ensure changement $c$ (dictionnaire intervention $\to$ nouvelle date), ou $\varnothing$
\If{$u < p_{\mathrm{swap}}$} \Comment{swap}
  \State $i \gets \mathcal{U}(\mathcal{I})$, \quad $j \gets \mathcal{U}(\mathcal{I} \setminus \{i\})$
  \If{$x_j \in \mathcal{S}_i$ \textbf{et} $x_i \in \mathcal{S}_j$ \textbf{et} $x_i \neq x_j$}
    \State \Return $\{i \to x_j,\; j \to x_i\}$
  \EndIf
  \State \Return $\varnothing$
\Else \Comment{déplacement}
  \State $i \gets \mathcal{U}(\mathcal{I})$
  \If{$u < p_{\mathrm{loc}}$}
    \State $s \gets x_i + \mathcal{U}(\{-r, \dots, r\} \setminus \{0\})$ \Comment{local : affine}
  \Else
    \State $s \gets \mathcal{U}(\mathcal{S}_i \setminus \{x_i\})$ \Comment{global : diversifie}
  \EndIf
  \If{$s \in \mathcal{S}_i$} \State \Return $\{i \to s\}$ \EndIf
  \State \Return $\varnothing$
\EndIf
\end{algorithmic}
\end{algorithm}
```

## Algorithme 6 : température initiale (`calibrer_t0`)

```latex
\begin{algorithm}[H]
\caption{\textsc{CalibrerT0}$(x, n, p_0)$}
\begin{algorithmic}[1]
\Require affectation $x$, nombre d'essais $n$, taux d'acceptation visé $p_0$ (ex. $0{,}5$)
\Ensure température initiale $T_0$
\State $D \gets \emptyset$
\For{$k = 1$ \textbf{à} $n$}
  \State $c \gets \textsc{Voisin}(x)$
  \If{$c \neq \varnothing$ \textbf{et} $\Delta C(x, c) > 0$ \textbf{et} $\Delta V(x, c) = 0$}
    \State $D \gets D \cup \{\Delta C(x, c)\}$ \Comment{variation d'objectif seule}
  \EndIf
\EndFor
\State $\bar\Delta \gets$ moyenne de $D$
\State \Return $T_0 = -\bar\Delta / \ln p_0$ \Comment{$e^{-\bar\Delta / T_0} = p_0$}
\end{algorithmic}
\end{algorithm}
```

## Algorithme 7 : recuit simulé (`recuit`)

```latex
\begin{algorithm}[H]
\caption{\textsc{Recuit}$(x^0, \mathit{tLimite})$}
\begin{algorithmic}[1]
\Require solution initiale $x^0$ (glouton), temps limite
\Ensure meilleure solution rencontrée $x^\star$
\State $x \gets x^0$, \quad $x^\star \gets x^0$
\State $T \gets \textsc{CalibrerT0}(x, n, p_0)$, \quad $T_0 \gets T$
\State $\alpha \gets \rho^{1 / N}$ \Comment{$N$ : nombre de paliers estimé dans le temps limite}
\While{temps écoulé $< \mathit{tLimite}$}
  \For{$k = 1$ \textbf{à} $L$} \Comment{palier de température}
    \State $c \gets \textsc{Voisin}(x)$
    \If{$c = \varnothing$} \State \textbf{passer} au $k$ suivant \EndIf
    \State $\mathit{ancien} \gets \{\, i \to x_i \mid i \in c \,\}$
    \State $\delta \gets$ appliquer $c$ à $x$ \Comment{\texttt{ev.assign(c)} renvoie $\Delta C$}
    \If{$\delta < 0$ \textbf{ou} $u < e^{-\delta / T}$}
      \If{$x \prec x^\star$} \State $x^\star \gets x$ \Comment{copie des dates} \EndIf
    \Else
      \State appliquer $\mathit{ancien}$ à $x$ \Comment{annulation}
    \EndIf
  \EndFor
  \State $T \gets \alpha \, T$ \Comment{refroidissement géométrique}
  \If{$V(x) > \varepsilon$}
    \State $\lambda \gets \gamma \, \lambda$ \Comment{la faisabilité devient de plus en plus prioritaire}
  \EndIf
  \State enregistrer (temps, $T$, $C(x)$, $C(x^\star)$, taux d'acceptation) \Comment{\texttt{Convergence}}
\EndWhile
\State \Return $x^\star$
\end{algorithmic}
\end{algorithm}
```

$\Delta V = 0$ dans `CalibrerT0` : sinon la pénalité $\lambda \Delta V$ (ordre $10^5$) écrase les
variations d'objectif (ordre 1 à 100) et la température reste trop haute pendant tout le recuit
(constaté : aucune amélioration du glouton sur A_01 et A_05).
$\alpha$ est calculé pour que $T$ atteigne $\rho \, T_0$ ($\rho = 10^{-3}$) à la fin du temps limite ;
$N = (\text{temps restant} \times \text{itérations/s mesurées au calibrage}) / L$.

Une itération coûte un appel à `assign` (deux en cas de refus), en $O(D \cdot |\Omega| \log |\Omega|)$.

## Algorithme 8 : descente finale (`descente`)

```latex
\begin{algorithm}[H]
\caption{\textsc{Descente}$(x, \mathit{tLimite})$}
\begin{algorithmic}[1]
\Require affectation $x$, temps limite
\Ensure minimum local $x$ pour les déplacements et les swaps
\Repeat
  \State \textit{amélioré} $\gets \textbf{faux}$
  \ForAll{$i \in \mathcal{I}$ dans un ordre aléatoire}
    \State $s^\star \gets \arg\min_{s \in \mathcal{S}_i} \Delta C(x, i \to s)$
    \If{$\Delta C(x, i \to s^\star) < 0$}
      \State $x_i \gets s^\star$, \quad \textit{amélioré} $\gets \textbf{vrai}$
    \EndIf
  \EndFor
  \ForAll{$i \in \mathcal{I}$, $j \in \mathcal{I}$ en cours sur une période commune avec $i$}
    \If{le swap $(i, j)$ est valide \textbf{et} $\Delta C(x, \{i \to x_j, j \to x_i\}) < 0$}
      \State échanger $x_i$ et $x_j$, \quad \textit{amélioré} $\gets \textbf{vrai}$
    \EndIf
  \EndFor
\Until{\textbf{non} \textit{amélioré} \textbf{ou} temps écoulé $\geq \mathit{tLimite}$}
\State \Return $x$
\end{algorithmic}
\end{algorithm}
```

## Algorithme 9 : métaheuristique complète (`main`)

```latex
\begin{algorithm}[H]
\caption{\textsc{MétaHeuristique}$(\mathit{tLimite})$}
\begin{algorithmic}[1]
\Require instance, temps limite total
\Ensure meilleure solution trouvée
\State $x^0 \gets \textsc{Glouton}(1, \lambda, \cdot)$ \Comment{algorithme 2, avec réparation}
\State $x^\star \gets \textsc{Recuit}(x^0, \; 0{,}9 \cdot \mathit{tLimite} - \text{temps écoulé})$
\State $x^\star \gets \textsc{Descente}(x^\star, \; \text{temps restant})$
\State \Return $x^\star$
\end{algorithmic}
\end{algorithm}
```

## Paramètres de départ (à régler sur les instances de réglage)

| Paramètre | Valeur de départ | Rôle |
|---|---|---|
| $p_{\mathrm{swap}}$ | 0,3 | part des swaps parmi les mouvements |
| $p_{\mathrm{loc}}$, $r$ | 0,8 ; 5 | déplacements locaux (affinage) vs globaux (diversification) |
| $p_0$, $n$ | 0,5 ; 500 | calibrage de $T_0$ |
| $L$ | $|\mathcal{I}|$ | itérations par palier |
| $\rho$ | $10^{-3}$ | $T_{\text{final}} = \rho \, T_0$ ; $\alpha$ en est déduit automatiquement |
| $\gamma$ | 1,01 | croissance de $\lambda$ tant que la solution courante est infaisable |
