# Air France punctuality analysis

Ce projet analyse la performance de ponctualité des vols Air France pour 2023 et 2024. Il s’appuie sur SQL (DuckDB) pour l’extraction, la transformation et le calcul de plusieurs KPI, puis exporte les résultats en CSV vers Power BI pour approfondissement.

---

## Structure du projet

```
├── README.md               # Documentation projet
├── airfrance.db            # Base DuckDB principale
├── pbix
│   ├── AirFrance.pbix      # Dashboards
├── data
│   ├── raw
│   │   ├── FLIGHTS_2023.csv
│   │   ├── FLIGHTS_2024.csv
│   │   ├── REF_AIRCRAFT.csv
│   │   ├── REF_AIRLINES.csv
│   │   ├── REF_DELAY.csv
│   │   └── airport_ref.json
│   └── export
│       └── flights_final.csv  # Résultat final pour dataviz
└── sql
    ├── 1_extract.sql      # Chargement & normalisation des sources
    ├── 2_transform.sql    # Enrichissements & pipeline intermédiaire
    ├── 3_kpis.sql         # Calcul des KPI avancés
    └── 4_export.sql       # Export CSV final
```

---

## Lancer le pipeline

1. **Initialiser DuckDB**

   ```bash
   duckdb airfrance.db
   ```
2. **Charger les scripts**

   ```bash
   .read sql/1_extract.sql
   .read sql/2_transform.sql
   .read sql/3_kpis.sql
   .read sql/4_export.sql
   ```
3. **Vérifier l’export**
   Le CSV `data/export/flights_final.csv` contient la table prête pour visualisation.

---

## Hypothèses et choix méthodologiques

### Flatten et export CSV
Le besoin principal était d'exporter la table principale, donc de flatten l’ensemble des tables pour fournir un dataset CSV unique, sans perdre aucune information.

### Incohérence codes-retard
Le jeu de données présentait une incohérence: certains vols en retard n’avaient pas de code de retard, tandis que d’autres, à l’heure, en possédaient. Cette problématique est restée car il est difficile de distinguer un vol à l’heure ayant subi un incident technique non consigné d’un vol retardé sans raison renseignée.

### Conservation des colonnes
Toutes les colonnes (y compris doublons FR/EN) ont été conservées pour conserver l'ensemble des informations.

### Indicateurs de ponctualité

* Création de `IS_ON_TIME_DEPARTURE` et `IS_ON_TIME_ARRIVAL` (comparaison ACT vs SCH)

### Traitement des codes de retard

* Regroupement des cinq colonnes de codes en un tableau (NULL exclus).
* Tableau `[NULL]` si aucun code valide pour conserver la ligne.
* UNNEST pour générer une ligne par code et faciliter la jointure 1 --> N avec la table `delay`.
* Mapping des codes non présents dans `delay` en `"##"`, tout en conservant le code initial.

### Clé unique de vol (`FLIGHT_ID`)
Construction d’une clé combinant `FLIGHT_NUMBER`, `DEP_SCH_UTC` et `DEP_IATA_CODE` pour garantir l’unicité et simplifier la traçabilité des KPI.

---

## KPI intégrés

| KPI                       | Définition                                                            |
| ------------------------- |-----------------------------------------------------------------------|
| ORIGIN\_YEAR              | Année d’origine du vol extraite du nom de fichier (2023 ou 2024)      |
| IS\_NATIONAL              | TRUE si le vol est national (`DEP_COUNTRY_CODE` = `ARR_COUNTRY_CODE`) |
| IS\_CANCELLED             | TRUE si `DEP_ACT_UTC` est NULL                                        |
| DELAY\_MINUTES\_DEPARTURE | Différence en minutes entre `DEP_ACT_UTC` et `DEP_SCH_UTC` (arrondi)  |
| IS\_ON\_TIME\_DEPARTURE   | TRUE si `DEP_ACT_UTC` <= `DEP_SCH_UTC`, FALSE sinon                   |
| DELAY\_MINUTES\_ARRIVAL   | Différence en minutes entre `ARR_ACT_UTC` et `ARR_SCH_UTC`            |
| IS\_ON\_TIME\_ARRIVAL     | TRUE si `ARR_ACT_UTC` <= `ARR_SCH_UTC`, FALSE sinon                   |

Note: les vols annulés (IS_CANCELLED = TRUE) sont exclus du calcul des retards dans Power BI, ils ne sont pas comptabilisés dans le total des vols pour le calcul de taux de retard.