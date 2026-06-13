# maker-fdm

> Maker disciplines for FDM-printed builds and embedded UI documentation.

## Skills (2)

| Skill | Triggers When |
|---|---|
| `bom-validation-workflow` | Validating a Bill of Materials (BOM) for a multi-component physical build (≥5 parts). Catches missing fasteners, wrong sizes, supplier-vs-stock mismatches, hidden cost spikes before purchase orders go out |
| `embedded-ui-svg-doc-from-source` | Documenting an embedded device GUI (ESP32/Arduino touchscreens with LovyanGFX/TFT_eSPI/U8g2/LVGL) for end-user instructions, printable manuals, or design reviews — when the source code already contains the drawing calls (`gfx.fillRect`, `lv_obj_set_pos`, etc.) |

## Pattern Compound

A typical maker workflow:
1. `bom-validation-workflow` — validate parts list before ordering
2. Print, assemble, test
3. Flash embedded firmware to the controller
4. `embedded-ui-svg-doc-from-source` — generate user-facing documentation from the GUI source code

Both skills prevent common waste: incorrect BOM = wrong parts ordered (€/€€€ + delay). Manually traced UI screenshots = stale documentation, drift from source.

## Installation

```bash
git clone https://github.com/Ed3Design/ed3design-skill-bundles
ln -s "$(pwd)/ed3design-skill-bundles/maker-fdm/skills"/* ~/.claude/skills/
```

Or via Claude Code marketplace (when registered):
```
/plugin install ed3design-skill-bundles/maker-fdm
```

## Related Bundles

- `cad-design` — parametric design + CAD scripting (the design step before the BOM)
- `token-savers` — `image-preprocessing-helper` for handling BOM photos efficiently
- `schema-discipline` — useful when BOM data lives in a database (parts inventory, etc.)

## License

MIT.
