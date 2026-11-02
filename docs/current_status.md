# Current project status — 2 November 2026

The historical status log is preserved under
[history](history/current_status_before_20261102_closeout.md). This page is the
current snapshot; the older log is evidence rather than active instructions.

## Operational campaign

PR148 merged into develop at48e2831693fc4abe0657c82197a2e884a61e99d2.
Public2231948/source334827d5 passed248tests without failures/errors/skips.
All terminal accounting completed0:0; source/runtime/engine/original-receipt,
license, dependency and exclusive-allocation checks passed. The accepted
receipt and original JSON copies remain versioned.

The [human launch recipe](experiments/npad_pyomo_serial_launch_20261102.md)
prepares86future scientific solves, six controls and one final consolidation:
93newsubmissions. Four completed h300 pilots are reused, never restarted.
Fresh quota must support the declared48GiB budget and qualified reserves.
Submit in hold, verify the complete graph and release once. No private
submission/release receipt has yet been received in this snapshot; do not
infer execution from a recipe or software merge.

Keep seed42, common Pyomo, native8h/job12h, one ordered lane per solver,
exclusive allocations and the population/memory/identity/closure/storage gates.
HiGHS16 remains a time-censored observation without a usable incumbent.
Its objective/gap remain null and the planned HiGHS arms remain in the campaign.

## PR144 reader closeout

The reader branch incorporates the merged operational files by original Git
blobs. Article/Appendices B–E now explain the bounded reading scope, finite
campaign, configured versus actual CPU use, and versioned data delivery.
Gurobi/HiGHS remain the reader-facing solver scope; excluded histories stay
on GitHub. Original Appendix A, bibliography keys/authors, approved title,
question/SO1–SO4, mathematics, numerical inputs and original results are preserved.

The metadata/claim reconciliation is bounded:38retained records,33main citations,
32ordered-family checks, targeted primary passages and four access-limited
sources. It does not certify38fulltexts reread or complete Rosa chapter/table
overlap. Original search chronology and full author/ORCID identities beyond
the retained checks remain explicit source/author facts rather than invented
results or a changed systematic review.

The newly reported t16 archives are not yet present in the documented local
directories. Their original collector metadata are saved separately; the
article's audited numerical tables retain the first t1pair. No new map or plan
is fabricated for a cell without an incumbent.

## Data, Zenodo and publication

Existing0.2.0 is publicly released/open:
[10.5281/zenodo.22751909](https://doi.org/10.5281/zenodo.22751909).
The refreshed public API metadata lists12files; no archive was redownloaded
in this refresh. The [data release plan](../data/manifests/zenodo_release_plan_20261102.json)
distinguishes that deposit from41locally prepared derivatives/450057392bytes,
pending per-asset review, a proposed next version and eventual anonymous-byte
verification. No new DOI, upload or publication has occurred. A later data
version will retain all90configuration states and actually returned outputs.

PR144still requires qualification/Ready and its own develop merge approval.
After that merge, open a separate main promotion PR for Quarto/Pages and fresh
snapshot-bound approval. Article/appendix PDF generation remains deferred.
Final PDF/TeX download validation belongs to the authorized publication step;
do not reuse an old Pages approval or describe planned downloads as current.
