# Design system

Canon product UI: the category standard played straight, with Linear and the Stripe dashboard as the craft bar.
The tool should disappear into the task. Alternatives considered: [../docs/direcciones-de-diseno.md](../docs/direcciones-de-diseno.md).

## Tokens

All tokens are defined in [src/app/globals.css](src/app/globals.css) as CSS custom properties and exposed to Tailwind via
`@theme inline` (`bg-superficie`, `text-tinta-2`, `border-borde-fuerte`…). Never hard-code colours in components.

| Token | Role | Light | Dark |
|---|---|---|---|
| `plano` | page ground, bottom action bar | `#f5f6f8` | `#0b0d10` |
| `superficie` | cards, inputs, top bar | `#ffffff` | `#14171c` |
| `superficie-2` | table headers, hover fills, segmented tracks, disabled inputs | `#f0f2f5` | `#1b1f26` |
| `tinta` / `tinta-2` / `tenue` | primary text / labels / help and secondary (≥4.5:1 on `superficie`) | `#0e1621` / `#48525f` / `#667080` | `#edf0f4` / `#b3bbc6` / `#8a939f` |
| `borde` / `borde-fuerte` | dividers and card borders / control borders | `#e2e5ea` / `#ccd2da` | `#252a32` / `#353c46` |
| `acento` / `acento-fuerte` / `acento-suave` | primary action, selection, focus / hover / selected-row fill | `#2266d4` / `#1a51ab` / `#e9f0fc` | `#4b8cf0` / `#7cabf5` / `#172338` |
| `bueno`, `advertencia`, `critico` (+ `-texto`) | semantic states; `-texto` variants for text on tints | | |
| `serie-1` / `serie-2` | chart series: blue = consumo / pagos, orange = generación / ahorros | `#2a78d6` / `#eb6834` | `#3987e5` / `#d95926` |

The accent only marks primary actions, current selection and focus, never decoration.

## Theme

`html[data-theme="light" | "dark"]` pins the theme; without the attribute it follows `prefers-color-scheme`.
[src/lib/tema.ts](src/lib/tema.ts) stores the choice (`prefactibilidad:tema`) and its inline script sets the attribute
before first paint. `SelectorTema` in the top bar offers Sistema / Claro / Oscuro.

## Type

- One family: the system UI sans (Segoe UI Variable on Windows). Body is 14px/1.5.
- Scale: 12 (help, badges) · 13 (field labels, table row heads) · 14 (body, controls) · 15 semibold (section titles) ·
  18 / 24 semibold (KPI values) · 20 semibold (results title).
- All figures use `tabular-nums`. Numbers in tables are right-aligned.

## Layout

- Content is centred at max 1280px with 16 / 24px gutters.
- A sticky top bar holds the brand, the stepper and the actions. It is one row at ≥1280px and wraps the stepper to a second row below that.
- Every step ends in `BarraAcciones`, a sticky bottom bar with Volver on the left and the primary action on the right.
- Proyecto, at ≥1024px, has a 13rem sticky section index on the left. It shows the active section (scroll spy), a short state line, and error counts.
- Field grids run 1 / 2 / 3 / 4 columns at sm / lg / xl. The gaps are 16px horizontal and 20px vertical.

## Components ([src/components/ui.tsx](src/components/ui.tsx))

- **Seccion:** a 12px-radius card with a 1px border, a header row (title plus optional action) with a bottom divider, and 20px padding. Tables inside run flush to the edges (`-mx-5 -mt-5`).
- **Controls:** 36px tall (32px compact in tables), 6px radius, `borde-fuerte` border, a focus border in the accent plus a 3px accent ring at 20% opacity. Errors turn the border red through `Campo`'s `data-invalido`.
- **Boton:** `primario` (solid accent), `secundario` (bordered surface), `fantasma` (text). An optional Lucide icon sits on the left and is replaced by a spinner while loading.
- **SiNo:** a two-segment radio group; the selected segment is filled with the accent.
- **Aviso:** a tinted box with a Lucide icon per level. No coloured side stripes.
- **Insignia:** a small tinted badge with an inset ring.
- **Slide picker:** horizontal cards with a thumbnail of the template slide taken from `public/diapositivas/NN.jpg`.
  Regenerate them with `scripts/exportar-miniaturas.ps1`, which needs PowerPoint, whenever the template changes. A conditional slide whose
  condition isn't met is disabled: dashed border, greyed thumbnail, its note in the warning colour, and a "No disponible" badge.
- **Icons:** Lucide only, at 16px in buttons and 14px inline. No unicode glyphs.
- **Elevation:** borders only. A shadow appears only on floating overlays (the chart tooltip).

## Charts ([src/components/Graficos.tsx](src/components/Graficos.tsx))

The frames match `Seccion`: a header row with the title and description, then a 288px plot area. Series, axes, reference lines and
encodings are fixed by the spreadsheet; only their styling follows the tokens.

## Motion

Transitions run 150ms on colour, border and opacity. A step change fades in over 180ms, and stale KPIs dim during recalculation.
`prefers-reduced-motion` disables all motion.
