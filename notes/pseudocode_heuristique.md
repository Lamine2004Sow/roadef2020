# Pseudo-code du glouton (LaTeX)

Code destiné au rapport : les blocs `latex` se compilent tels quels avec le préambule ci-dessous.
Correspondance avec le code : `src/heuristique.py` (à écrire), `src/evaluation.py`, `src/indicateurs.py`.

## Préambule

```latex
\usepackage{amsmath, amssymb}
\usepackage{algorithm}
\usepackage[noend]{algpseudocode}
\floatname{algorithm}{Algorithme}
\algrenewcommand\algorithmicrequire{\textbf{Entrées :}}
\algrenewcommand\algorithmicensure{\textbf{Sortie :}}
\algrenewcommand\algorithmicfor{\textbf{pour}}
\algrenewcommand\algorithmicforall{\textbf{pour tout}}
\algrenewcommand\algorithmicdo{\textbf{faire}}
\algrenewcommand\algorithmicwhile{\textbf{tant que}}
\algrenewcommand\algorithmicif{\textbf{si}}
\algrenewcommand\algorithmicthen{\textbf{alors}}
\algrenewcommand\algorithmicelse{\textbf{sinon}}
\algrenewcommand\algorithmicreturn{\textbf{retourner}}
```

## Notations

```latex
\begin{itemize}
  \item $\mathcal{I}$ : ensemble des interventions, $T$ : nombre de périodes.
  \item $x_i \in \{1, \dots, \min(t^{\max}_i, T)\}$ : date de début de l'intervention $i$ ;
        $x$ est une affectation partielle, $x_i = \varnothing$ si $i$ n'est pas encore placée.
  \item $\mathcal{S}_i = \{1, \dots, \min(t^{\max}_i, T)\}$ : dates de début possibles de $i$.
  \item $\mathrm{obj}(x)$ : objectif ROADEF (risque moyen et excès au quantile $\tau$, pondérés par $\alpha$).
  \item $V(x)$ : violations (dépassements des bornes $\min$ / $\max$ des ressources
        + périodes d'exclusion violées).
  \item Coût pénalisé : $C(x) = \mathrm{obj}(x) + \lambda \, V(x)$.
  \item $\Delta C(x, i \to s) = C(x') - C(x)$ où $x'$ est égal à $x$ sauf $x'_i = s$
        (calcul incrémental : \texttt{Evaluation.delta}).
\end{itemize}

\paragraph{Score de difficulté.} Pour chaque intervention,
\[
  \mathrm{score}_i = a \, \mathcal{N}\!\left(\frac{W_i D_i}{F_i}\right)
                   + b \, \mathcal{N}\!\left(\frac{E_i}{F_i}\right)
                   + c \, \mathcal{N}\!\left(\frac{\mathrm{Reg}_i}{\bar R_i}\right)
\]
où $\mathcal{N}$ désigne la normalisation dans $[0, 1]$ (division par le maximum sur $\mathcal{I}$),
$F_i = |\mathcal{S}_i|$, $D_i$ la durée moyenne, $W_i$ la charge relative moyenne,
$E_i$ le nombre d'exclusions, $\mathrm{Reg}_i$ le regret et $\bar R_i$ le risque moyen de $i$.

\paragraph{Pénalité par défaut.}
\[
  \lambda = \beta \cdot \frac{1}{|\mathcal{I}|} \sum_{i \in \mathcal{I}} \bar R_i,
  \qquad \beta = 10,
\]
de sorte que réduire une violation soit prioritaire sur réduire le risque.
```

## Algorithme 1 : meilleure date d'une intervention (`meilleure_date`)

```latex
\begin{algorithm}[H]
\caption{\textsc{MeilleureDate}$(x, i, k)$}
\begin{algorithmic}[1]
\Require affectation partielle $x$, intervention $i$ non placée, taille de liste $k \geq 1$
\Ensure date de début $s^\star \in \mathcal{S}_i$
\State $L \gets \emptyset$
\ForAll{$s \in \mathcal{S}_i$}
  \State $\delta_s \gets \Delta C(x, i \to s)$ \Comment{\texttt{ev.delta(\{i: s\})}}
  \State $L \gets L \cup \{(s, \delta_s)\}$
\EndFor
\State trier $L$ par $\delta_s$ croissant
\If{$k = 1$}
  \State \Return la date $s$ du premier élément de $L$
\Else
  \State \Return une date tirée uniformément parmi les $\min(k, |L|)$ premières de $L$ \Comment{GRASP}
\EndIf
\end{algorithmic}
\end{algorithm}
```

Complexité : $O(|\mathcal{S}_i|)$ appels à $\Delta C$, chacun en $O(D \cdot |\Omega| \log |\Omega|)$
avec $D$ la durée et $|\Omega|$ le nombre de scénarios (moyenne et quantile des périodes touchées).

## Algorithme 2 : construction gloutonne (`glouton`)

```latex
\begin{algorithm}[H]
\caption{\textsc{Glouton}$(k, \lambda, \text{graine})$}
\begin{algorithmic}[1]
\Require instance, taille de liste $k$, pénalité $\lambda$, graine aléatoire
\Ensure affectation complète $x$
\State calculer $\mathrm{score}_i$ pour tout $i \in \mathcal{I}$
\State $\sigma \gets$ interventions triées par $\mathrm{score}_i$ décroissant \Comment{\texttt{sort\_interventions}}
\State $x_i \gets \varnothing$ pour tout $i \in \mathcal{I}$ \Comment{\texttt{Evaluation} vide}
\ForAll{$i$ dans l'ordre $\sigma$}
  \State $s^\star \gets \textsc{MeilleureDate}(x, i, k)$
  \State $x_i \gets s^\star$ \Comment{\texttt{ev.assign(\{i: s*\})}}
\EndFor
\If{$V(x) > 0$}
  \State $x \gets \textsc{Réparer}(x)$
\EndIf
\State \Return $x$
\end{algorithmic}
\end{algorithm}
```

Complexité : $O\big(\sum_{i} |\mathcal{S}_i|\big)$ appels à $\Delta C$, plus le tri en $O(|\mathcal{I}| \log |\mathcal{I}|)$.

## Algorithme 3 : réparation des violations (`reparer`)

```latex
\begin{algorithm}[H]
\caption{\textsc{Réparer}$(x, \mathit{maxIter})$}
\begin{algorithmic}[1]
\Require affectation complète $x$ avec $V(x) > 0$, nombre maximal d'itérations
\Ensure affectation $x$ de coût pénalisé inférieur ou égal
\For{$\mathit{it} = 1$ \textbf{à} $\mathit{maxIter}$}
  \If{$V(x) = 0$} \State \textbf{arrêter} \EndIf
  \State $\mathcal{I}_V \gets$ interventions en cours sur une période où une ressource
         ou une exclusion est violée
  \State $\textit{amélioré} \gets \textbf{faux}$
  \ForAll{$i \in \mathcal{I}_V$}
    \State $s^\star \gets \arg\min_{s \in \mathcal{S}_i} \Delta C(x, i \to s)$
    \If{$\Delta C(x, i \to s^\star) < 0$}
      \State $x_i \gets s^\star$
      \State $\textit{amélioré} \gets \textbf{vrai}$
    \EndIf
  \EndFor
  \If{\textbf{non} \textit{amélioré}}
    \State refaire les lignes 6 à 10 avec $\mathcal{I}_V \gets \mathcal{I}$ \Comment{bornes $\min$}
  \EndIf
  \If{\textbf{non} \textit{amélioré}}
    \State appliquer le premier swap $(i, j)$, $i \in \mathcal{I}_V$, $j \in \mathcal{I}$, tel que $\Delta C < 0$
  \EndIf
  \If{\textbf{non} \textit{amélioré}} \State \textbf{arrêter} \Comment{minimum local} \EndIf
\EndFor
\State \Return $x$
\end{algorithmic}
\end{algorithm}
```

Utile surtout pour les bornes $\min$ des ressources, qui ne peuvent pas être garanties pendant la construction.

## Algorithme 4 : glouton randomisé multi-départ (`grasp`)

```latex
\begin{algorithm}[H]
\caption{\textsc{GRASP}$(n, k, \lambda, \mathit{tLimite})$}
\begin{algorithmic}[1]
\Require nombre de relances $n$, taille de liste $k > 1$, pénalité $\lambda$, temps limite
\Ensure meilleure affectation trouvée $x^\star$
\State $x^\star \gets \varnothing$, \quad $C^\star \gets +\infty$
\For{$r = 1$ \textbf{à} $n$}
  \If{temps écoulé $\geq \mathit{tLimite}$} \State \textbf{arrêter} \EndIf
  \State $x \gets \textsc{Glouton}(k, \lambda, r)$ \Comment{graine $r$}
  \If{$C(x) < C^\star$}
    \State $x^\star \gets x$, \quad $C^\star \gets C(x)$
  \EndIf
\EndFor
\State \Return $x^\star$
\end{algorithmic}
\end{algorithm}
```

Comme $\lambda$ est grand, minimiser $C$ privilégie d'abord les solutions réalisables ($V = 0$),
puis le meilleur objectif parmi elles.
