TABLE: markets



\- id (PK)

\- code (string) → ej: omie

\- name (string)

\- country (string) → ES

\- currency (string) → EUR

\- unit (string) → €/MWh

\- created\_at (timestamp)





TABLE: price\_days



\- id (PK)

\- market\_id (FK → markets.id)

\- date (date)

\- avg\_price (float)

\- min\_price (float)

\- max\_price (float)

\- base\_load\_price (float)

\- peak\_load\_price (float)

\- hours\_count (int)

\- import\_status (string) → pending / ok / error

\- source\_updated\_at (timestamp)

\- created\_at (timestamp)

\- updated\_at (timestamp)

UNIQUE (market\_id, date)



TABLE: price\_hours



\- id (PK)

\- price\_day\_id (FK → price\_days.id)

\- hour\_index (int) → 1..24

\- hour\_start (timestamp)

\- hour\_end (timestamp)

\- price (float)

\- created\_at (timestamp)

UNIQUE (price\_day\_id, hour\_index)



TABLE: day\_comparisons



\- id (PK)

\- market\_id (FK → markets.id)

\- date (date)

\- previous\_date (date)

\- avg\_diff (float)

\- avg\_diff\_pct (float)

\- min\_diff (float)

\- max\_diff (float)

\- cheapest\_hour\_today (int)

\- cheapest\_hour\_yesterday (int)

\- most\_expensive\_hour\_today (int)

\- most\_expensive\_hour\_yesterday (int)

\- created\_at (timestamp)

\- updated\_at (timestamp)

UNIQUE (market\_id, date)





