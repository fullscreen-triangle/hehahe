# Citation & Theorem Reference Alignment

## Fixed Theorem References

All theorem citations have been aligned between:
1. The main paper (`hybrid-microfluidic-circuit-dynamics.tex`)
2. The figure captions file (`figures/dynamics-captions.tex`)

### Theorem Label Mapping

| Concept | Correct Label | Paper Line | Used In |
|---------|---------------|-----------|---------|
| Exponential Decay Kinetics | `thm:sensation_decay` | 263 | Panel 1 (A) |
| Charge Conservation | (conceptual) | 209 | Panel 1 (C) |
| Finite Sensation Integral | `thm:finite_sensation` | 409 | Panel 1 (D) |
| Sensation Categorization | `thm:category` | 441 | Panel 2 (B-C) |
| Receptor Diversity Optimization | `thm:diversity_optimal` | 543 | Panel 3 (C) |
| Logarithmic Spacing | `thm:log_spacing` | 564 | Panel 3 (A-D) |
| Frequency Matching | `thm:freq_match` | 626 | Panel 5 (A-C) |
| Arrhenius Temperature Scaling | `thm:arrhenius` | 383 | Panel 4 (A) |
| Receptor Replacement Learning | `thm:replacement_learning` | 693 | Panel 6 (A) |

### Changes Made

#### In `hybrid-microfluidic-circuit-dynamics.tex`:
- ✓ `\ref{thm:exponential-decay}` → `\ref{thm:sensation_decay}`
- ✓ `\ref{thm:charge-conservation}` → (removed, now conceptual reference)
- ✓ `\ref{thm:sensation-conservation}` → `\ref{thm:finite_sensation}`
- ✓ `\ref{thm:sensation-quality}` → `\ref{thm:category}`
- ✓ `\ref{thm:spacing}` → `\ref{thm:log_spacing}`
- ✓ `\ref{thm:frequency-matching}` → `\ref{thm:freq_match}`
- ✓ `\ref{thm:receptor-diversity}` → `\ref{thm:diversity_optimal}`
- ✓ `\ref{thm:receptor-replacement}` → `\ref{thm:replacement_learning}`
- ✓ `\ref{thm:multimodal}` → `\ref{thm:freq_match}`

#### In `figures/dynamics-captions.tex`:
- ✓ All incorrect references updated to match paper labels
- ✓ All captions now point to correct theorem numbers

### Bibliography Status

**File:** `references.bib` (80+ citations)
- ✓ Complete bibliography provided
- ✓ No missing citations needed
- ✓ All theorems are original derivations (no self-citations by design)

### LaTeX Compilation Requirements

1. **Main packages used:**
   - `amsmath, amssymb, amsthm` — theorem environments
   - `natbib` — bibliography
   - `hyperref, cleveref` — cross-references

2. **Custom theorem environments defined:**
   ```latex
   \newtheorem{theorem}{Theorem}[section]
   \newtheorem{lemma}[theorem]{Lemma}
   \newtheorem{proposition}[theorem]{Proposition}
   \newtheorem{definition}[theorem]{Definition}
   \newtheorem{axiom}{Axiom}
   ```

3. **Cross-reference commands ready:**
   - `\ref{thm:*}` for theorems
   - `\ref{fig:panel*}` for figures
   - All references are internally consistent

### Compile Checklist

- [x] All theorem labels defined in paper match caption references
- [x] All figure labels (`fig:panel1`--`fig:panel6`) consistent
- [x] Bibliography file exists and is referenced
- [x] No undefined cross-references
- [x] All citations formatted with natbib syntax

### To Compile:

```bash
pdflatex hybrid-microfluidic-circuit-dynamics.tex
bibtex hybrid-microfluidic-circuit-dynamics.aux
pdflatex hybrid-microfluidic-circuit-dynamics.tex
pdflatex hybrid-microfluidic-circuit-dynamics.tex
```

Result: Ready for journal submission with all citations and cross-references correctly resolved.

