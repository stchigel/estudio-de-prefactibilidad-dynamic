---
version: 1
slug: "src-app-page-tsx"
primary_target: "src/app/page.tsx"
related_targets: ["src/components"]
---

# Surface: prefactibilidad wizard (all five steps)

Mode: Operate. Audience: internal sales/engineering staff on desktop; Resultados sometimes shown to clients.
Priorities from the user: overall look and navigation, and the long Proyecto form. Light and dark with a manual toggle.
Must not change: field labels, units, help texts, chart encodings, step order.

## Direction contract

THESIS: A working product UI that disappears into the task. It refuses the current look of a stack of identical bordered boxes under a pill-button step row, where nothing says where you are or what is missing.
OWN-WORLD: The category standard played straight (canon), with Linear and the Stripe dashboard as the craft bar. A cool neutral scale (white surfaces on a faintly grey ground; near-black panels in dark mode), one blue accent reserved for primary actions, selection and focus, and semantic state colours. System sans with tabular figures, 36px controls, 1px borders, no shadows except on overlays, and Lucide icons.
STORY: The user always sees which step they are on, moves through long forms with an index, and has the next action always within reach. Results read as a clean summary they can show a client.
FIRST VIEWPORT: A sticky top bar with the brand at left, the five-step stepper (check marks on done steps, the current step filled) and, at right, the theme switch, Nueva propuesta and Salir. Below it sits the step content. In Proyecto, a sticky section index on the left shows the active section and error counts. A sticky bottom action bar holds Volver at left and the primary action at right.
FORM: canon (category standard) chosen by the user; seed:6d06b5df2b6971ba
FINISH: unreviewed and undocumented is unfinished; this build ends with the finish review, the verdict, DESIGN.md, and every shipping raster carrying its provenance
