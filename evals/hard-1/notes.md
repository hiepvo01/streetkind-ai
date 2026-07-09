## Open question: `clients[0].physicalAssaultRisk`

`expected.json` leaves this at the default `0`, but it's an unresolved judgment call, not a validated value.

The transcript has the volunteer directly witnessing the shove ("earlier we'd actually seen the two of them shoving each other"), which is the same kind of "volunteer directly witnessed a physical altercation" pattern that justified `physicalAssaultRisk: 3` in `hard-3/expected.json`. The difference: in hard-3 the shove happens live at the point of contact with the volunteer, who then actively manages an escalating situation (calls CCTV/rangers, stays to protect her). In hard-1 the shoving is a discrete, already-concluded incident recounted somewhat after the fact — Maya then approaches the base separately, with no indication of an active volunteer role in stopping or managing the altercation itself.

Current prompt guidance (`config/prompts/incident.txt`, RISK MINIMISATION SCALES) says this should lean toward `0` given no active volunteer intervention role — but it's genuinely borderline. The model has set `physicalAssaultRisk: 2` here in multiple runs. Needs a domain-expert call (e.g. Harriet) on whether a witnessed-but-concluded scuffle like this should register on the scale at all, before this fixture value is treated as ground truth either way.
