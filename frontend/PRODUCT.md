# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

Internal Dynamic Energy staff (sales and engineering) working on office desktops and laptops. They produce several solar pre-feasibility studies a month, know the domain and the original Excel well, and want speed and accuracy over guidance. Occasionally the Resultados screen is shown on screen to a client during a meeting.

## Product Purpose

Replaces the manual flow *facturas → Excel → PowerPoint* with a five-step assistant: upload the client's electricity bills (AI extraction), review 12 months of consumption, fill the project data, choose among automatically proposed kit combinations, and review results to export the completed Excel and the client PowerPoint. Success: a correct, presentable study produced in minutes, with numbers identical to the validated spreadsheet.

## Positioning

A faithful, validated replica of the company's own calculation spreadsheet, plus automatic bill reading and option search over the company's own kit catalog. The numbers must match the Excel; the tool adds speed, not a different model.

## Operating Context

- Inputs: distributor bills (PDF, scans, phone photos), market parameters that change rarely between studies (dollar value, CAMMESA costs, rates), and per-client data.
- Outputs: the original Excel template filled in, and a PowerPoint built from the company template.
- The draft persists in the browser (localStorage); runs on an office PC or a small VPS, optionally behind a password.
- Spanish (Argentina) UI, comma decimals, $ / U$D currencies, kWh / kWp / m² units.

## Capabilities and Constraints

- Field labels, units, help texts and option names mirror the spreadsheet and are deliberate; do not rename them.
- Charts (consumption vs generation, ROI curve, financing payments vs savings) must keep how they read: same series, axes, and encodings.
- Five fixed steps: Facturas, Consumos, Proyecto, Opciones, Resultados. Earlier steps can be revisited.
- Light and dark themes, following the OS by default with a manual toggle.

## Brand Commitments

None binding for this internal tool. Name shown: "Dynamic Energy" / "Estudio de prefactibilidad solar".

## Evidence on Hand

Real example bills in `../ejemplos-facturas/`, example studies in `../ejemplos-prefactibilidad/`. No logo asset in the repo.

## Product Principles

1. Numbers first: values, units and states must be legible at a glance and never ambiguous.
2. Expert speed: dense, scannable, keyboard-friendly; no hand-holding beyond the existing help texts.
3. Always know where you are: which step, which section, what is missing or wrong.
4. Presentable when needed: Resultados must hold up on a meeting-room screen without a separate mode.
