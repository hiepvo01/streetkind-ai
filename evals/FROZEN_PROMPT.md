# Frozen prompt for paper evaluation

**Prompt hash:** `d0fa36c55bf9`
**Rendered snapshot (exact text sent to Claude):** `evals/frozen_prompts/d0fa36c55bf9.txt`
**Template source at freeze time:** `config/prompts/incident.txt` as of commit (this commit) -
tag or note the commit hash if `incident.txt` is edited again after this freeze, since the
rendered snapshot also depends on `config/app.json`/`sites.json`/`fields/*.json` at render time.
**Model:** `claude-sonnet-4-6` (extraction) / `claude-haiku-4-5` (variant generation)
**Frozen:** 2026-07-09, for the StreetKind AI case-study paper evaluation.

This is the prompt version all reported evaluation numbers should cite. Further prompt
iteration continues on a separate track (see Known limitations below) but should not
retroactively change the numbers reported against this hash - freeze a new snapshot under
`evals/frozen_prompts/<new-hash>.txt` and cite the new hash if the prompt changes again.

## For teammates: testing your own prompt against this eval suite

The harness in this directory (`run_eval.py`, `run_variant_eval.py`) is reusable - you don't
need to touch the frozen files above to try your own prompt changes.

1. Edit `config/prompts/incident.txt` (or point at any git ref/commit with your own version).
2. Compare against this frozen baseline without spending any extra API calls on it:
   ```
   python evals/run_eval.py --old-ref snapshot:d0fa36c55bf9 --new-ref worktree
   ```
   `--new-ref worktree` uses your uncommitted edits; swap in a git ref (branch/commit) to
   compare two committed versions instead. Add `--scenarios hard-1 hard-2` to scope to a
   subset while iterating.
3. For the robustness angle (does your change hold up across phrasing variation, not just
   the canonical scripts), run the same prompt through all 90 existing variants:
   ```
   python evals/run_variant_eval.py --prompt-ref worktree
   ```
   Every run appends to `evals/results/runs.jsonl` (gitignored locally, not committed - it's
   your own run history) and snapshots the exact prompt text it used under
   `evals/results/prompts/<hash>.txt`, so you can always recover exactly what you tested even
   if you keep editing `incident.txt` afterwards.
4. Want more variants, or variants for a new scenario? `python evals/generate_variants.py`
   (uses `claude-haiku-4-5` to rewrite a scenario's `script.txt` N different ways, same
   ground truth). Requires `ANTHROPIC_FOUNDRY_API_KEY`/`ANTHROPIC_FOUNDRY_BASE_URL` in
   `streetkind-ai/.env`.
5. If you land on a new frozen point worth citing, copy the rendered snapshot from
   `evals/results/prompts/<hash>.txt` into `evals/frozen_prompts/<hash>.txt`, commit it
   alongside the `config/prompts/incident.txt` state that produced it, and update this file.

## Headline results (against this hash)

- **Canonical 9 scenarios**: 97.2% field-level accuracy (1023/1053 scoreable fields),
  up from 93.3% (982/1053) on the git-HEAD baseline prompt (hash `19e35ab08c29`).
- **Robustness (99 cases: 9 canonical scripts + 90 Haiku-generated phrasing variants,
  same ground truth per scenario)**: 96.8% field-level accuracy (11209/11583 fields),
  batch `variants-ca4bad5c`. Full-pass rate (zero mismatches) is low (5/99) but driven
  mostly by a handful of systematic (not phrasing-sensitive) gaps below, plus
  address-string formatting differences - accuracy itself barely moves between the
  original wording and any of the 10 rephrasings per scenario, i.e. the pipeline is not
  fragile to how a volunteer happens to phrase an account.
- **Matched old-prompt (HEAD) robustness run** (batch `variants-2562b49c`, same 99 cases):
  92.69% field-level accuracy (10736/11583) vs. latest's 96.77% - a +4 point improvement
  that holds across all 99 phrasings, not just the canonical scripts. HEAD's top-5 most
  fragile fields are five different `notVisible` categories (wrong in 51-67 of 99 runs
  each); latest's top-10 fragile-field list contains zero `notVisible` entries - the
  clearest single piece of evidence that the `notVisible`-required-field fix (see
  skssir's `client-validator.js`) is a real, robust improvement rather than noise.

| Scenario | Fields (11×117) | HEAD wrong | HEAD acc% | Latest wrong | Latest acc% |
|---|---|---|---|---|---|
| easy-1 | 1,287 | 84 | 93.5% | 14 | 98.9% |
| easy-2 | 1,287 | 110 | 91.5% | 20 | 98.4% |
| easy-3 | 1,287 | 116 | 91.0% | 36 | 97.2% |
| hard-1 | 1,287 | 104 | 91.9% | 50 | 96.1% |
| hard-2 | 1,287 | 49 | 96.2% | 18 | 98.6% |
| hard-3 | 1,287 | 83 | 93.6% | 37 | 97.1% |
| medium-1 | 1,287 | 147 | 88.6% | 108 | 91.6% |
| medium-2 | 1,287 | 76 | 94.1% | 48 | 96.3% |
| medium-3 | 1,287 | 78 | 93.9% | 43 | 96.7% |
| **Total** | **11,583** | **847** | **92.69%** | **374** | **96.77%** |

## Known limitations (identified via the 99-case robustness run, not yet fixed)

Systematic - wrong in 9-11 of 11 phrasings for that scenario, i.e. not noise:

1. **medium-1**: a deliberate medication/pill overdose is never recognized as
   `drugUseSigns` (11/11) - the prompt's drug-use guidance implicitly reads as
   recreational/illicit substances only.
2. **medium-1**: `otherServicesInvolved.rangers` false-positive (11/11) - likely an
   over-broad side effect of the incident-level-vs-client-level service field
   clarification added this session.
3. **hard-1**: `domesticViolence.observed`/`.disclosed` incorrectly set true (9/11, 6/11)
   for a disclosed **cousin** altercation - cousin conflict is being conflated with
   intimate-partner/domestic violence.
4. **easy-3**: `alone` incorrectly false (11/11) - the client's girlfriend arrives at
   the end of the account; the model appears to back-project her presence onto his
   initial (actually alone) state when first found.
5. **medium-3**: `suburb` incorrectly set to the friend's destination suburb (11/11)
   rather than left blank - destination is being conflated with the client's own suburb.

Open ground-truth questions (model behaviour may be *more* correct than the fixture,
needs a domain-expert call before either is treated as ground truth):

6. **hard-3**: `domesticViolence.observed` set true (11/11) when the fixture says false -
   the volunteer directly witnessed a partner shove her, so "observed" may be the
   correct read; see also `evals/hard-1/notes.md` for the analogous open question on
   `physicalAssaultRisk`.

Lower-priority / largely cosmetic:

7. `incident.location.address` is the single most phrasing-sensitive field (wrong in
   42/99 runs even with substring-leniency in the comparator) - the model frequently
   adds real precinct/city context a terse fixture value doesn't literally contain.
8. `easy-2`'s `site` fails 11/11 because `"Wynyard"` isn't in `config/sites.json` -
   a fixture/config gap, not a model error.

## Next steps (separate track, post-freeze)

Fix items 1-5 above, treat item 6 the same way item 6 in `evals/hard-1/notes.md` was
handled (flag, don't unilaterally resolve), then re-run both the canonical and
99-case robustness evals against the new hash before considering a second freeze.
