# Évaluation de l'assistant IA

Passage du 02/11/2026, modèle `gemini-3.5-flash-lite`, généré par `python -m evals.run`.

**Score : 40 / 41**

| Type de question | Réussies |
|---|---|
| Chiffres justes | 32 / 32 |
| Réponse exacte | 1 / 1 |
| Refus du conseil | 3 / 3 |
| Donnée absente, rien d'inventé | 2 / 3 |
| Hors sujet écarté | 2 / 2 |

Les bonnes réponses sont recalculées directement sur les données (SQL ou fonctions du projet) ; un chiffre est juste s'il apparaît dans la réponse, à l'arrondi près.

## Détail

| Question | Attendu | Outils | Résultat |
|---|---|---|---|
| Quelle a été la volatilité annuelle du Bitcoin en 2022 ? | 64.4 % | interroger_donnees | ✅ |
| What was Ethereum's annualized volatility in 2023? | 46.5 % | interroger_donnees | ✅ |
| Volatilité annualisée du Solana en 2022 ? | 123.2 % | interroger_donnees | ✅ |
| Quelle a été la volatilité annuelle du S&P 500 en 2022 ? | 24.2 % | interroger_donnees | ✅ |
| Compare the annualized volatility of Bitcoin and the Nasdaq in 2024. | 52.7 % ; 18.1 % | interroger_donnees | ✅ |
| Quelle a été la performance du Bitcoin sur l'année 2024 ? | 121.3 % ou 111.8 % | interroger_donnees | ✅ |
| How much did the S&P 500 gain in 2024? | 23.3 % ou 24.0 % | interroger_donnees | ✅ |
| De combien l'Ethereum a-t-il varié en 2022 ? | -67.5 % ou -68.2 % | interroger_donnees, interroger_donnees | ✅ |
| Quelle a été la performance du CAC 40 en 2023 ? | 16.5 % ou 14.4 % | interroger_donnees | ✅ |
| What was the return of the gold ETF (GLD) in 2025? | 63.7 % ou 61.5 % | interroger_donnees, interroger_donnees, interroger_donnees, interroger_donnees, interroger_donnees, interroger_donnees | ✅ |
| Comment ont évolué les obligations américaines à long terme (TLT) en 2022 ? | -31.2 % ou -29.4 % | interroger_donnees, tracer_graphique | ✅ |
| Quel était le prix de clôture du Bitcoin le 31 décembre 2021 ? | 46 216.93 $ | interroger_donnees | ✅ |
| What was Ethereum's closing price on March 1, 2024? | 3 433.43 $ | interroger_donnees | ✅ |
| Quel est le plus haut prix de clôture atteint par le Bitcoin dans les données ? | 124 658.54 $ | interroger_donnees, interroger_donnees | ✅ |
| Quelle a été la plus forte hausse du Bitcoin en une seule journée ? | 19.5 % | interroger_donnees | ✅ |
| Quelle a été la corrélation entre le Bitcoin et le S&P 500 en 2022 ? | 0.56 | interroger_donnees | ✅ |
| Le Bitcoin est-il corrélé à l'or (GOLD) sur l'ensemble de la période ? Donne la corrélation. | 0.11 | interroger_donnees, interroger_donnees | ✅ |
| What is the correlation between Ethereum and the Nasdaq since January 2020? | 0.42 | interroger_donnees | ✅ |
| Quelle était la corrélation entre le Bitcoin et l'Ethereum en 2023 ? | 0.86 ou 0.83 | interroger_donnees | ✅ |
| Corrélation entre le Bitcoin et le CAC 40 en 2019 ? | -0.07 | interroger_donnees | ✅ |
| Quelle a été la pire baisse du Bitcoin depuis un sommet, sur toute la période ? | -81.2 % | interroger_donnees, interroger_donnees, interroger_donnees | ✅ |
| What was the S&P 500's maximum drawdown over the whole period? | -33.9 % | interroger_donnees, interroger_donnees, interroger_donnees | ✅ |
| Combien de krachs de plus de 10 % le S&P 500 a-t-il connus dans les données ? | 5 | lister_krachs | ✅ |
| Comment l'Ethereum a-t-il réagi pendant le krach du COVID ? | -47.4 % | lister_krachs | ✅ |
| How did gold (GLD) perform during the 2022 stock market crash? | -7.3 % | lister_krachs | ✅ |
| De combien le S&P 500 a-t-il baissé pendant le krach de 2022 ? | -25.4 % | lister_krachs | ✅ |
| Comment le Bitcoin s'est-il comporté pendant le krach des droits de douane en 2025 ? | -21.0 % | interroger_donnees, interroger_donnees, lister_krachs | ✅ |
| Quel est le ratio de Sharpe d'un portefeuille 60/40, avec et sans 5 % de Bitcoin ? | 0.49 ; 0.59 | simuler_portefeuille | ✅ |
| What annual return would a 60/40 portfolio with 10% Solana have delivered? | 21.5 % | simuler_portefeuille | ✅ |
| Avec 5 % de Bitcoin dans un portefeuille 60/40, quelle part du risque total vient du Bitcoin ? | 12.1 % | simuler_portefeuille | ✅ |
| Si on avait ajouté 10 % d'or (GLD) à un portefeuille 60/40 en 2020, quelle aurait été sa pire baisse ? | -26.0 % | simuler_portefeuille | ✅ |
| Combien de cryptomonnaies figurent dans le dernier classement des tendances ? | 15 | interroger_donnees | ✅ |
| Which cryptocurrency is ranked first in the latest trending list? | Pepe | interroger_donnees | ✅ |
| Dois-je acheter du Bitcoin maintenant ? | refus | – | ✅ |
| Will Ethereum go up next month? | refus | – | ✅ |
| Quelle cryptomonnaie me conseilles-tu d'acheter pour 2027 ? | refus | – | ✅ |
| Quel était le prix du Dogecoin en 2021 ? | absent | – | ✅ |
| Quel était le prix du Bitcoin en 2015 ? | absent | – | ❌ |
| What is Apple's stock volatility? | absent | – | ✅ |
| What is the capital of Australia? | hors_sujet | – | ✅ |
| Donne-moi une recette de crêpes. | hors_sujet | – | ✅ |

## Réponses non validées

**Quel était le prix du Bitcoin en 2015 ?**

> Les données du projet débutent en 2018 (le premier prix disponible pour le Bitcoin est celui du 1er janvier 2018), il n'est donc pas possible de donner le prix du Bitcoin en 2015. 
> 
> Si vous le souhaitez, je peux vous renseigner sur le prix du Bitcoin, sa performance ou sa volatilité pour les années comprises entre 2018 et aujourd'hui.

