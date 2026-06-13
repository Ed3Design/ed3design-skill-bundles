# cad-design

> Parametric CAD design disciplines for makers, mechanical engineers, and product designers.

## Skills (4)

| Skill | Domain |
|---|---|
| `cad-api-scripting` | Python for commercial CAD platforms (Fusion 360, etc.) + OpenSCAD scripts. Programmatic modeling, geometry generation, automation |
| `cad-construction` | Structured workflow: design concept → parametric CAD model. Component decomposition, parameter hierarchy, construction sequencing. The **HOW** of CAD work |
| `mechanical-design-principles` | Design rules for elegant + manufacturable + serviceable solutions. Tool-less assembly, monolithic parts, overhang/wall guidelines. The **WHAT and WHY** of mechanical design |
| `image-to-mesh-cad-workflow` | End-to-end: 2D concept image → 3D parametric CAD. Uses image-to-3D-mesh services (Tripo3D etc.) when manual outline tracing is unreliable |

## Pattern Compound

`mechanical-design-principles` (WHAT/WHY) → `cad-construction` (HOW) → `cad-api-scripting` (AUTOMATE). These three skills layer naturally: principles inform construction, construction informs scripting. `image-to-mesh-cad-workflow` is the pre-step when you have an image but no clean outline.

## Installation

```bash
git clone https://github.com/Ed3Design/ed3design-skill-bundles
ln -s "$(pwd)/ed3design-skill-bundles/cad-design/skills"/* ~/.claude/skills/
```

Or via Claude Code marketplace (when registered):
```
/plugin install ed3design-skill-bundles/cad-design
```

## Related Bundles

- `maker-fdm` — BOM validation + embedded UI documentation for physical builds
- `token-savers` — `image-preprocessing-helper` for handling CAD screenshots and BOM photos efficiently

## License

MIT.
