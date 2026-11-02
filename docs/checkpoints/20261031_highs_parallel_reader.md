# HiGHS 1.15.1 parallelism — reader revision, 31 October 2026

The researcher requested a methodological explanation and additional detail in Appendix C. This change adds a version-specific methodology paragraph and Section C4.1. It distinguishes MIP tree parallelism from LP-relaxation parallelism, prospective parallel=on profiles from the preserved h215 parallel-search-off observation, configured thread ceilings from measured use, and fixed-seed temporal repetitions from independent instance samples.

Primary sources checked: https://github.com/ERGO-Code/HiGHS/blob/v1.15.1/docs/src/parallel.md and https://github.com/ERGO-Code/HiGHS/releases/tag/v1.15.1 . The release states that parallel simplex is not used for MIP LP relaxations. No standalone-LP speedup, root-LP parallelism or16-thread performance claim is inferred.

Local validation: scripts/check_manuscript.py accepted33cited references; tests/test_manuscript.py passed59tests. No new PDF was rendered, no solver or NPAD command was run for this editorial change, and Appendix A, author directions, original results and bibliographic records are unchanged. The operational Gurobi/HiGHS campaign remains a separate prospective PR requiring its own public NPAD qualification and merge approval.
