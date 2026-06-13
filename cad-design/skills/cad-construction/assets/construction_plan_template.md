# CAD Construction Plan: [PROJECT_NAME]

> Numerical values in this template (tolerances, wall thicknesses, insert sizes) are starting points drawn from `mechanical-design-principles`. Adjust to the specific project but do not re-invent — the reference values there are the authoritative source.

## 1. Functional Requirements

### Primary requirements
- [Requirement 1]
- [Requirement 2]

### Secondary requirements
- [Requirement 3]
- [Requirement 4]

### Conflicts & compromises
| Conflict | Resolution | Rationale |
|----------|------------|-----------|
| [e.g., protection vs handling] | [e.g., quick-release with gasket] | [e.g., IP67 + tool-less opening] |

### Environmental conditions
- **Temperature range:** [e.g., -10 °C to +60 °C]
- **Moisture / exposure:** [e.g., salt spray, outdoor]
- **UV:** [e.g., continuous outdoor]
- **Mechanical loads:** [vibration, shock, etc.]

---

## 2. Component Decomposition

### Main assembly: [NAME]

#### Component 1: [NAME]
- **Function:** [description]
- **Material:** [PLA / PETG / ASA / ABS / PA-CF / aluminum / etc.]
- **Manufacturing:** [FDM 3D print / SLA / CNC / sheet metal]
- **Critical interfaces:** [fit to Component 2, tolerance class]
- **Print orientation:** [if FDM, state orientation and reason]

#### Component 2: [NAME]
- **Function:** [description]
- **Material:** [material]
- **Manufacturing:** [method]
- **Critical interfaces:** [interfaces]
- **Print orientation:** [if FDM]

#### Purchased parts
- [e.g., M4 heat-set inserts × 8]
- [e.g., O-ring 80 × 3 mm NBR70]
- [e.g., Stainless steel screws M4 × 16 × 8]

---

## 3. Parameter Table

### Tier 1: Primary parameters (independent base dimensions)
| Parameter | Value | Unit | Description |
|-----------|-------|------|-------------|
| `hauptmass_laenge` | 120 | mm | Outer length |
| `hauptmass_breite` | 85 | mm | Outer width |
| `hauptmass_hoehe` | 40 | mm | Outer height |
| `nozzle_diameter` | 0.6 | mm | For wall-thickness derivation |

### Tier 2: Derived parameters (formulas)
| Parameter | Formula | Description |
|-----------|---------|-------------|
| `wandstaerke` | `nozzle_diameter * 4` | 4 perimeters, nozzle-dependent |
| `innenhoehe` | `hauptmass_hoehe - wandstaerke * 2` | Height minus two wall thicknesses |
| `nutbreite_oring` | `dichtung_durchmesser * 1.05` | O-ring groove width |

### Tier 3: Tolerances & fasteners
| Parameter | Value | Unit | Description |
|-----------|-------|------|-------------|
| `schrauben_durchmesser` | 4 | mm | M4 screws |
| `durchmesser_gewindeeinsatz` | 5.2 | mm | M4 heat-set + 0.2 tolerance |
| `spielpassung_toleranz` | 0.3 | mm | Moving parts |
| `presssitz_toleranz` | -0.15 | mm | Permanent fits |

---

## 4. Construction Sequence

### Step 1: Setup
1. Create new design / document
2. Create user parameters from Parameter Table (Phase 3)
3. Create top-level component structure

### Step 2: Main geometry

For each major feature:

1. **Sketch:** [description]
   - Plane: [e.g., XY construction plane]
   - Geometry: [rectangle with rounded corners, circles, etc.]
   - Constraints: [symmetric to origin, coincident, parallel, etc.]
   - Dimensions: [`parameter_name`, not literal numbers]

2. **Feature:** [description]
   - Profile: [which sketch profile]
   - Operation: [extrude / revolve / loft / sweep]
   - Distance / angle: `parameter_name`
   - Result: [New body / Join / Cut]

### Step 3: Detail features
1. Fillets and chamfers (parameterized radii)
2. Mounting holes and inserts
3. Gasket grooves
4. Cable entries / ports
5. Drainage holes if outdoor

### Step 4: Sub-components
- [List of sub-assemblies with parameter references]

### Step 5: Joints & assembly
- [Joint types between components]
- [Interference checks]

---

## 5. Manufacturing Notes

### FDM 3D print parameters (if applicable)
- **Layer height:** [e.g., 0.2 mm]
- **Infill:** [e.g., 30 % gyroid]
- **Perimeters:** [e.g., 4 walls]
- **Support:** [where needed / not needed, with justification]
- **Print orientation:** [with reasoning — which surface on the bed, which faces up]

### Post-processing
1. [e.g., Press heat-set inserts at 230 °C with soldering iron]
2. [e.g., Sand sealing surfaces flat]
3. [e.g., Deburr drainage holes]

---

## 6. Assembly Instructions

1. [Step 1]
2. [Step 2]
3. [Step 3]

### Required tools
- [e.g., Soldering iron for heat-set inserts]
- [e.g., 3 mm Allen key]

---

## 7. Test & Validation

### Function tests
- [ ] [Test 1, e.g., Water spray test for IP rating]
- [ ] [Test 2, e.g., Open / close 20 cycles]

### Measurements
- [ ] [Measurement 1, e.g., Actual vs designed wall thickness]
- [ ] [Measurement 2, e.g., Fit of purchased parts]
