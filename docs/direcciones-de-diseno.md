# Design directions (Nov 2026 redesign)

The redesign on branch `rediseno-interfaz` follows the **category standard**: a clean, conventional
product UI (neutral greys, one blue accent) at the polish level of Linear or the Stripe dashboard.

These three alternatives were considered and set aside. They are recorded here in case the tool
should take on more identity later. All three keep the same five steps, the standard controls, every label,
and how each chart reads.

## 1. Esquema unifilar (electrical single-line diagram)

- **World:** a single-line diagram on an engineering sheet.
- **Palette:** a deep switchboard-navy top band over cool drafting-paper white (in dark mode, a navy-black sheet),
  ink line work, and solar amber reserved to mean "energized".
- **Signature move:** the step bar drawn as a busbar. Completed segments light up amber and the current step is
  a closed breaker node. In Proyecto, a sticky "feeder" index of sections taps into each section, showing which
  one is active and how many errors it has.
- **Raises:** a KPI that changes after a sensitivity tweak stays marked until it has been seen; flat fills with no
  gradients or shadows; a fixed size ramp so ROI, Inversión, Ahorro and TIR lead.
- **Risk:** the line motifs read as decoration if overdone.

## 2. Ficha técnica (PV module datasheet)

- **World:** a manufacturer's module datasheet.
- **Palette/type:** dense spec tables with a units column, a solid colour band heading each section, and tabular
  figures everywhere.
- **Signature move:** every field row reads like a spec line (label · value · unit), and sections are numbered
  bands with a sticky index.
- **Risk:** the most familiar of the three, and close to what many engineering tools already look like.

## 3. Tablero de partidas (airport gate board and boarding pass)

- **World:** a departure board plus a segmented boarding pass.
- **Palette:** high-contrast neutral panels, with one alert colour reserved for change.
- **Signature move:** when a sensitivity input changes, the affected Resultados KPIs re-rank and stay lit until
  they have been seen. Results are split into labelled segments with tabular figures.
- **Risk:** strong for clarity but weaker on identity with the solar and electrical world.
