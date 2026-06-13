# Thought: Roadmap Stage Metrics

Track how long each pipeline stage takes and how many tokens it consumes, and surface that data on the roadmap page dot tooltips.

Each filled dot on the roadmap should show time taken (in hours) and tokens used on hover. Data stored as start/end time + start/end token count columns on the features table — one pair per stage (7 stages × 4 columns = 28 new columns). The tooltip computes duration and token delta and appends them to the existing hover text.

This is a developer/project-owner visibility feature — no user-facing changes beyond the enriched tooltips.
