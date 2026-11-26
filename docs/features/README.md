# Feature archive

When every feature of a milestone is `passing`, its entries move from
`feature_list.json` to `<milestone>.json` here (for example `M0.json`), with
the same fields and the shape `{"milestone": "M0", "features": [...]}`.
`check_harness.py` reads these files too: archived features must be `passing`,
IDs stay unique, and `depends_on` in `feature_list.json` can point at archived
features. `scripts/session-brief.sh` counts them in its totals.
