# CAD Construction Reference

General reference for parametric CAD construction — applies broadly across commercial CAD systems (Fusion 360, SolidWorks, Onshape, Inventor, NX, FreeCAD).

## Parametric design principles

### User parameters
- Central control of all dimensions through named parameters
- Naming convention: `category_description` (e.g., `diameter_main`, `height_housing`)
- Dependencies: derived dimensions through formulas (e.g., `wall_thickness = nozzle_diameter * 4`)
- One source of truth: every number exists exactly once in the parameter table

### Component hierarchy
```
Component (main assembly)
├── Body (main structure)
├── Component (sub-assembly 1)
│   ├── Body (part)
│   └── Body (part)
└── Component (sub-assembly 2)
```

Keep the tree shallow. Deep trees are hard to navigate and hard to refactor.

### Construction workflow
1. **Requirements** — functional requirements captured
2. **Decomposition** — logical breakdown into components
3. **Parameters** — central parameter table defined
4. **Sketches** — 2D sketches with constraints
5. **Features** — extrude, revolve, loft, sweep — all parameter-driven
6. **Assembly** — joints and constraints between components

## Typical construction patterns

### Housing with lid
- Parameters: `housing_length`, `housing_width`, `housing_height`, `wall_thickness`
- Bodies: base, lid, gasket
- Features: fillets, screw bosses, cable entries

### Mount / bracket
- Parameters: `mount_spacing`, `screw_diameter`, `material_thickness`
- Bodies: base plate, mounting features
- Features: slotted holes for adjustment, reinforcement ribs

### Outdoor / marine protective housing
- Consider IP rating (IP66 / IP67 typical for marine)
- Gasket grooves (O-ring): `groove_width = ring_diameter * 1.05`
- Drainage: holes at low points
- Material selection: PETG / ASA for UV resistance, not PLA

## 3D-print considerations in CAD

The mechanical rules (overhang angle, layer adhesion, wall-thickness grid, tolerance values) live in `mechanical-design-principles`. This section covers how to *apply* them during CAD construction — the CAD-workflow-specific habits, not the rules themselves.

### Apply print orientation during CAD, not after
- Decide orientation during component decomposition (Phase 2 of construction), before sketching begins
- Mark it on the CAD document (comment in the first sketch, or in the component's description)
- Every critical surface is evaluated against that orientation: is it support-free, bridge-printable, or does the geometry need redesign?

### Parametric tolerance handling
- Do not hard-code tolerance values. Create parameters like `tolerance_press`, `tolerance_slide`, `tolerance_insert` and reference them in sketches.
- When a tolerance turns out wrong after print-testing, changing one parameter updates every place it's used.
- For the actual numerical values of press-fit, clearance-fit, heat-set insert, and O-ring groove tolerances: `mechanical-design-principles` → Decision heuristics.

### Post-processing considerations in the CAD model
- Heat-set inserts: design the bore diameter as `M_nominal + tolerance_insert`, not as a literal number
- Sealing surfaces: either design extra material for sanding, or design for a gasket — CAD should reflect which approach is chosen
- Thread features: model threads are for visualization only. Functional threads are heat-set inserts, tapped holes, or printed threads (reliable only at M6 and above for FDM).

## Automation (pointer to cad-api-scripting)

When the construction plan is mature and you want to:
- Import the parameter table into the CAD system programmatically
- Generate repetitive geometry
- Create reusable modules / macros

→ switch to the `cad-api-scripting` skill. That skill handles code generation and debugging for CAD APIs. The boundary is clean: this skill defines WHAT to build, `cad-api-scripting` writes the code that builds it.
