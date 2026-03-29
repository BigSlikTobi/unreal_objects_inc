```markdown
# Design System Specification: The Kinetic Ledger

This design system is built to transform high-density technical data into an authoritative, editorial experience. It rejects the "generic SaaS" aesthetic of gray boxes and thin borders in favor of **Tonal Layering** and **Intentional Asymmetry**. The goal is to make the user feel like they are operating a high-end, live-data instrument rather than just browsing a web app.

---

## 1. Overview & Creative North Star
**Creative North Star: "The Digital Curator"**
The system treats data as a curated exhibit. We achieve "Authority" through bold typography scales and "Transparency" through layered, translucent surfaces. By breaking the rigid 12-column grid with overlapping elements and varying card heights, we create a "Live" atmosphere that feels reactive and bespoke.

---

## 2. Colors & Surface Philosophy
The palette is rooted in deep slates and high-contrast accents, optimized for a "Light-on-Dark" primary experience while maintaining full WCAG compliance in Light Mode.

### The "No-Line" Rule
**Explicit Instruction:** Designers are prohibited from using 1px solid borders to section off the UI.
* **The Strategy:** Define boundaries through background shifts. A `surface-container-low` element sitting on a `surface` background creates a sophisticated, architectural break that 1px lines cannot replicate.
* **The Exception:** If a boundary is functionally required for accessibility, use a "Ghost Border" (the `outline-variant` token at 15% opacity).

### Glass & Texture
* **Glassmorphism:** Use `surface-container-high` with a 12px `backdrop-blur` for floating panels (e.g., Command Palettes or Expanded Card States). This allows the "live" data underneath to bleed through, reinforcing the brand’s "Transparency."
* **Signature Gradients:** For primary CTAs and critical data headers, use a subtle linear gradient from `primary` to `primary-container` at a 135-degree angle. This adds "soul" and depth to an otherwise flat technical interface.

---

## 3. Typography: The Editorial Voice
We utilize a dual-typeface system to balance technical precision with authoritative impact.

| Level | Token | Font | Size | Weight | Character |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Display** | `display-lg` | Space Grotesk | 3.5rem | 700 | Brutalist, Impactful |
| **Headline**| `headline-md` | Space Grotesk | 1.75rem | 600 | Authoritative |
| **Title** | `title-lg` | Inter | 1.375rem | 600 | Clear, Navigational |
| **Body** | `body-md` | Inter | 0.875rem | 400 | Highly Readable |
| **Label** | `label-sm` | Inter | 0.6875rem | 700 | Technical, All-Caps |

**Editorial Direction:** Use `display` tokens for top-level data metrics (e.g., Total Objects). Use `label-sm` with 0.05em letter-spacing for metadata and bot-activity timestamps to evoke a "terminal" feel.

---

## 4. Elevation & Depth: Tonal Layering
Traditional drop shadows are replaced by a "Stacking" logic. Depth is a result of color proximity, not artificial lighting.

1. **Level 0 (Base):** `surface` (#060e20)
2. **Level 1 (Sections):** `surface-container-low` (#06122d)
3. **Level 2 (Cards/Modules):** `surface-container` (#05183c)
4. **Level 3 (Interactive/Hover):** `surface-container-high` (#031d4b)

**Ambient Shadows:** For floating modals, use a shadow with a 40px blur, 0% spread, and color `on-surface` at 6% opacity. This mimics the soft glow of a high-end monitor in a dark room.

---

## 5. Components & Primitive Styles

### Cards & Data Modules
* **Execution:** No dividers. Use `Spacing: 6` (1.3rem) to separate internal card sections.
* **Hover State:** Transition background from `surface-container` to `surface-container-highest` and apply a subtle `primary` tint to the top-left corner (2px accent).

### Buttons (The Kinetic Set)
* **Primary:** Background `primary-container`, text `on-primary-container`. High-contrast, no shadow.
* **Secondary:** Ghost style. Transparent background with a `surface-variant` hover state.
* **Bot Activity (Specialty):** Background `primary-fixed-dim` (Subtle Blue) with a pulsing 2px dot of `primary`.

### Data Chips & Status
* **Approved:** `tertiary-container` text on `on-tertiary-fixed` background.
* **Rejected:** `error-container` text on `on-error-container` background.
* **Pending:** `amber` tokens (using `secondary-fixed` as a base for warmth).

### Input Fields
* **State:** Default state uses `surface-container-lowest` (pure black in dark mode) to create "wells" in the UI.
* **Focus:** Transition the `outline` token from 0% to 100% opacity over 200ms. No "glow" effects—keep it sharp and technical.

### Expansion Modules (Signature Component)
Since the dashboard is "Read-Only Focus," use card expansions to reveal "Live Bot Logs." When clicked, the card should animate from `surface-container` to a `surface-container-highest` glass panel that overlaps adjacent cards, breaking the grid.

---

## 6. Do’s and Don’ts

### Do
* **DO** use `Space Grotesk` for numbers. It feels more technical and "Unreal."
* **DO** use `surface-container-lowest` for background "wells" to house secondary data tables.
* **DO** use Lucide icons at `1.2rem` scale for standard actions, ensuring they use the `outline` color token.
* **DO** embrace white space. If data is "dense," give the containers massive outer margins (`Spacing: 10` or `12`).

### Don’t
* **DON'T** use `border-gray-200` or any 1px solid lines. It breaks the "curated" editorial feel.
* **DON'T** use rounded corners larger than `xl` (0.75rem). The brand is "Technical/Authoritative"; overly round corners feel too consumer-soft.
* **DON'T** use standard blue for links. Use `tertiary` (Emerald/Mint) for "Go" actions or `primary` (Slate-Blue) for navigation.
* **DON'T** use generic "Drop Shadows." If it doesn't look like it's made of light and glass, it doesn't belong.

---

## 7. Implementation Note: Tailwind Integration
When building, lean heavily on the `surface` tokens.
Example Card: `bg-surface-container hover:bg-surface-container-high transition-colors p-6 rounded-lg`
Example Header: `text-display-sm font-bold tracking-tight text-on-surface`
Example Glass: `bg-surface-container-highest/60 backdrop-blur-md`

This system is designed to feel "expensive." If a screen looks cluttered, increase the background contrast between the `surface` and `surface-container` rather than adding more lines.```
