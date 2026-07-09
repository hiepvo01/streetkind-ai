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

**Ground truth v2.1 (2026-07-09, post-freeze, does not change the prompt hash):** five
fixture corrections were applied after a review pass, described in "Ground truth
corrections" below. The prompt itself is unchanged - this is a re-diff of the same cached
extraction outputs against corrected fixtures, not a re-run (no new API calls). Numbers in
this document are current as of v2.1; anything citing the earlier 97.2%/96.8% figures is
stale.

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
   `streetkind-ai/.env`. **Do not regenerate variants for scenarios that already have
   recorded voice audio** - script text is locked once recording starts (see easy-2 below).
5. Genuinely ambiguous fields (a defensible judgment call, not a wrong/right extraction) can
   be tolerated rather than scored strictly - see `SCENARIO_TOLERANCES` in `run_eval.py`
   (currently just `medium-1`'s `clientConsciousness`, which accepts `{1, 3}`).
6. If you land on a new frozen point worth citing, copy the rendered snapshot from
   `evals/results/prompts/<hash>.txt` into `evals/frozen_prompts/<hash>.txt`, commit it
   alongside the `config/prompts/incident.txt` state that produced it, and update this file.

## Ground truth corrections (v2.1, applied after a review pass)

1. **Hard 1, Medium 1, Medium 2, Medium 3 — `drugUseSigns.observed` → `false`.** Defined
   `observed` strictly as "volunteer directly witnessed drug *use*" (not signs of use, not a
   disclosure). None of the 9 scenarios describe a volunteer literally watching someone take
   drugs - Hard 1's "pupils huge, grinding teeth" and Medium 3's "seemed drug-affected" are
   appearance/impression evidence (`visibleSigns`/`observed`-as-behavioural-judgment per the
   prompt's own rule, not witnessed use), and Medium 1/2's drug involvement is disclosed
   after the fact. Medium 3 additionally gets `visibleSigns: false → true` (the "seemed...
   not just alcohol" impression is visible evidence, not witnessed use). **After this
   correction, no scenario has `drugUseSigns.observed: true` anywhere in the fixture set -
   which is realistic (volunteers essentially never witness consumption directly) and makes
   this sub-field a pure fabrication-risk trap for the model. See the finding below: this is
   now empirically the second-most fragile field in the whole suite.**
2. **Hard 3 — `domesticViolence.observed` → `true`.** Resolves the open question flagged at
   the previous freeze: the volunteers directly watched the partner shove her, which is a
   witnessed act, matching the paper's own definition of what `observed` means for this
   category. The model had been "disagreeing" with the fixture on this every single run
   (11/11) - it was right.
3. **Easy 2 — `incident.site` → `""` (was `"Wynyard"`).** `"Wynyard"` was never a valid site
   key in `config/sites.json`. Voice recording has started for this scenario, so the
   transcript text is locked and `config/sites.json` cannot be changed mid-evaluation either
   (the prompt regenerates from config, so config is part of the frozen system) - the
   pipeline's actual behaviour (return empty rather than invent a site) is correct, and the
   fixture should expect that. `location.address` is unaffected and still expects
   `"Near Wynyard"`.
4. **Medium 1 — `clientConsciousness` tolerance, not a value change.** Both `1`
   (unconscious) and `3` (passed out) are defensible readings of "barely responsive,
   non-verbal, but responsive to her name" - the fixture keeps `3` but the harness now
   accepts either (`SCENARIO_TOLERANCES` in `run_eval.py`).
5. **Hard 1 — `physicalAssaultRisk` remains an open question, not resolved.** Unlike Hard 3
   (an actively-managed live situation), Hard 1's shove is a concluded incident recounted
   after the fact with no active volunteer role in it - the fixture keeps `0`, but this is a
   domain-expert call StreetKind should confirm, not a settled value. See
   `evals/hard-1/notes.md`.

## Headline results (against this hash, re-scored against v2.1 ground truth)

- **Canonical 9 scenarios**: 97.34% field-level accuracy (1025/1053 scoreable fields), up
  from 85.85% (904/1053) on the git-HEAD baseline prompt (hash `19e35ab08c29`). HEAD's number
  dropped sharply under the corrected ground truth (previously 93.3%) because HEAD predates
  every fix this session - it fails the `notVisible`-required-field convention, the
  `drugUseSigns.observed` correction, and the Hard 3 DV correction simultaneously, none of
  which it ever had a chance to get right.
- **Robustness (99 cases: 9 canonical scripts + 90 Haiku-generated phrasing variants, same
  ground truth per scenario)**: 96.98% field-level accuracy (11233/11583 fields), batch
  `variants-ca4bad5c`. Barely moved from the pre-correction 96.77% - the ground truth fix
  mostly changed *what* is wrong, not *how much*.
- **Matched old-prompt (HEAD) robustness**: 92.76% (10744/11583), batch `variants-2562b49c` -
  also barely moved from 92.69%.

| Scenario | Fields (11×117) | HEAD wrong | HEAD acc% | Latest wrong | Latest acc% |
|---|---|---|---|---|---|
| easy-1 | 1,287 | 84 | 93.5% | 14 | 98.9% |
| easy-2 | 1,287 | 101 | 92.2% | 9 | 99.3% |
| easy-3 | 1,287 | 116 | 91.0% | 36 | 97.2% |
| hard-1 | 1,287 | 115 | 91.1% | 57 | 95.6% |
| hard-2 | 1,287 | 49 | 96.2% | 18 | 98.6% |
| hard-3 | 1,287 | 72 | 94.4% | 26 | 98.0% |
| medium-1 | 1,287 | 131 | 89.8% | 86 | 93.3% |
| medium-2 | 1,287 | 71 | 94.5% | 39 | 97.0% |
| medium-3 | 1,287 | 100 | 92.2% | 65 | 94.9% |
| **Total** | **11,583** | **839** | **92.76%** | **350** | **96.98%** |

(Canonical single-script numbers - just the "original" case from each scenario's 11 - are a
subset of the table above; see "Headline results" bullets for the standalone 9-scenario
figure.)

## Finding: `drugUseSigns.observed`/`.visibleSigns` is the model's clearest fabrication-risk
   field, not a prompt bug

Post-correction, `incident.location.address` (cosmetic, phrasing-driven) and
`clients[0].drugUseSigns.observed` (32/99 wrong) are the two most fragile fields in the whole
suite - `.visibleSigns` is close behind (24/99). This is now a *named, evidence-backed
finding* rather than noise: distinguishing "volunteer witnessed drug use," "volunteer
observed a visible physical sign of drug use," and "client disclosed drug use" is a genuinely
subtle three-way distinction even for the humans who wrote this fixture set - the original
version of this suite got Hard 1/Hard 2/Medium 3's `observed` values inconsistent with the
prompt's own stated rule, and it took an external review to catch it. If a fine-tuned model
struggles with the same distinction at a ~1/3 error rate independent of phrasing, that is a
legitimate limitation to report, not evidence the prompt is broken - a targeted prompt fix
("never set `observed: true` unless the volunteer says they directly saw someone use/take
drugs") is a good candidate for the next prompt iteration, on the separate post-freeze track.

`Medium 1` sharpens this further: the model correctly sets `disclosed: true` (husband's
account) 11/11, but never infers `visibleSigns: true` from the physical symptoms (raised
pulse, vomiting, non-verbal) that accompany the disclosure - i.e. it can extract an explicit
statement but doesn't connect physical symptoms to the same category once a different
sub-field is already satisfied.

## Known limitations (identified via the 99-case robustness run, not yet fixed)

Systematic - wrong in most/all of 11 phrasings for that scenario, i.e. not noise:

1. **Medium 1**: `drugUseSigns.visibleSigns` never set true (11/11) despite `disclosed`
   being correctly true - see finding above.
2. **Medium 1**: `otherServicesInvolved.rangers` false-positive (11/11).
3. **Medium 1**: `additionalAid.mentalHealthAid` false-positive (11/11) - not described in
   the transcript.
4. **Hard 1**: `domesticViolence.observed`/`.disclosed` incorrectly set true for a disclosed
   **cousin** altercation - cousin conflict is being conflated with intimate-partner/
   domestic violence. (Distinct from the now-resolved Hard 3 question - Hard 3's `observed`
   was correct; this one is a real categorisation bug.)
5. **Easy 3**: `alone` incorrectly false (11/11) - the client's girlfriend arrives at the end
   of the account; the model appears to back-project her presence onto his initial (actually
   alone) state when first found.
6. **Medium 3**: `suburb` incorrectly set to the friend's destination suburb (11/11) rather
   than left blank - destination is being conflated with the client's own suburb.

Open ground-truth question (a domain-expert call, not yet resolved either way):

7. **Hard 1**: `physicalAssaultRisk` - see `evals/hard-1/notes.md` and correction #5 above.

Lower-priority / largely cosmetic:

8. `incident.location.address` is the single most phrasing-sensitive field (wrong in 42/99
   runs even with substring-leniency in the comparator) - the model frequently adds real
   precinct/city context a terse fixture value doesn't literally contain.

## Next steps (separate track, post-freeze)

Fix items 1-6 above, treat item 7 the same way item 5 in the corrections list was handled
(flag, don't unilaterally resolve without StreetKind), then re-run both the canonical and
99-case robustness evals against the new hash before considering a second freeze.
