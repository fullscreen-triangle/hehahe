# hehahe

A theory repository, not a codebase. ~354 indexed files, ~93% LaTeX prose
(8719 `section` + 1611 `heading` symbols vs ~800 code symbols). Treat the
documents as the primary artifact.

## Code/document search: `purpose`

Global usage rules for `purpose index` / `ask` / `ledger` live in the user-level
`~/.claude/CLAUDE.md`. The rules below are specific to *this* repo and override
the general advice where they conflict.

### `purpose ckg` — module contact graph

Full documentation: [ckg-usage.md](musculo-skeletal/ckg-usage.md). The lens is
committed at [.purpose/lens.toml](.purpose/lens.toml) and is tuned for this repo;
read its comments before editing, they record what was measured.

| You want | Use |
|---|---|
| Where is `X` defined? | `purpose ask "X"` |
| Which documents is this goal about? | `purpose ckg ask "<goal>"` |
| What else depends on this document? | `purpose ckg why <path>` |

### The scoping constraint — read before running `ckg`

**Never run `ckg` with `include.paths = []` on this repo.** Measured 2026-08-16:

| modules | `lens` | `build` | `why` | `ask` |
|---|---|---|---|---|
| 354 (unscoped) | 5–50 min (completes) | — | — | — |
| 149 (`olduvai-gorge/**`) | 51s | 21s | 34s | did not return in 300s |
| 27 (`olduvai-gorge/docs/**`) | — | 2s | — | 3s |

Two independent reasons, both structural rather than fixable by tuning. Note
that **runtime is not one of them** — the unscoped `lens` run does complete.

1. **The unscoped lens does not discriminate.** At 354 modules it puts 87% of
   modules in one component and prints its own warning that "τ is not
   discriminating between them"; goal saturation is exactly 50%, the threshold
   the usage doc gives for an indiscriminable goal. Scoping to
   `olduvai-gorge/**` moves density 0.494 → 0.292 and saturation 50% → 28%.
   Density does not fall by tuning alone because this repo is one research
   program restated across many documents, so every paper genuinely shares
   `oscillatory` (26%), `coupling` (25%), `information`, `entropy`. Those are
   the subject matter; stopwording them to force the density down is the
   degenerate lens §6 of the usage doc warns against.
2. **`ask` is the binding constraint.** Its dominator pass is what fails at 149
   modules. `lens`, `build`, `why`, and `floor` all still work there.

So: **scope to one program, run `ckg ask` at ~30 modules.** Swap the active
`paths` line in the lens (candidates are listed commented-out) and re-run
`purpose ckg build` before querying — `ask`/`why` read the lens stored in
`ckg.json`, not the file on disk.

### Interpreting results here

Expect low discrimination and do not mistake it for a tuning failure. On
`olduvai-gorge/docs/**` (27 modules), a goal like `cardiac oscillatory coupling`
returns 21 modules NECESSARY, all `seed` — ~78% saturation, well past the 50%
threshold at which the usage doc says a goal cannot be discriminated. That is a
true statement about the repo: these documents are one tightly-coupled
derivation chain. Consequently **`ckg why` is the more informative command here
than `ckg ask`** — "what would I break by editing this document" has a sharp
answer, "which documents is this about" mostly returns the whole program.

β* has stayed at 1.00 (149 modules) / 27.00 (27 modules) across tuning. Per §6
that is expected and is *not* a quality score — never report it as improvement.

### Caveats that bite in a prose repo

- The index holds **definitions and headings only**. Body text, citations,
  `\ref`/`\cite` cross-references, and equations are absent — so two papers that
  cite each other but share no section vocabulary will show **no contact**.
- **Filenames and paths are not indexed as terms.** Use Glob to find files.
- Never conclude something does not exist from a `purpose` miss; fall back to
  Grep/Glob.

### Rebuild after adding documents

```bash
purpose index && purpose ckg build     # index is stale as soon as papers are added
```
