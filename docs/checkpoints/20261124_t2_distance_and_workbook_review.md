# T2 distance comparison and revised-workbook review — 24 November 2026

PR164 corrects the derived SQLite comparison, with no edits to either user-supplied workbook, source database, frozen arc values or scientific builders. All original failed receipts and source commits are preserved. The helper maps only historical [-1,0) m round-off to a derived zero, classifies adjacent positive binary64 conversion values separately, and leaves larger/non-finite/negative differences or ambiguous identities rejected/unresolved. Source acquisition/routing provenance remains pending.

The existing transferred backup has unchanged SHA-256 `5f2ecca8c45a82b2d8fd815f8135b2c0ba19450bead26d8a3cc796e5b2bdb081`. Corrected comparison reconciles 262,072 selected product-indexed records (222,202 exact; 39,870 adjacent values), four normalised cache entries and 40 affected selected arc records. No selected pair is missing. This is numeric selected-graph reconciliation, not certification of a live source snapshot.

Forty-six local standard-library tests, including invalid-distance, genuine-difference, ambiguity, source-preservation and bootstrap-pin controls, passed. Ruff passed. New helper/controller/bootstrap hashes are updated together; old hashes and consumed commands remain historical.

The author-review XLSX hashes are recorded separately from frozen runtime input pins. Keyed numeric parameters are unchanged; three longitude cells differ by one binary64 step after Excel's round trip. All 18,086 CDA keys are unique. There are 111 groups/262 rows with identical source attributes except CDA and 325 groups/776 rows with repeated operator/type/static capacity. Private row/CDA lists remain local. Do not delete/coalesce those facilities without identity evidence.

The author explicitly confirmed that K scales both candidate declared-capacity bounds and existing expansion bounds (currently 25% of initial static capacity). Investment cost is proportional to the physical capacity actually installed after scaling, once. The current variables already represent those physical tonnes. K=2 allows at most +50% expansion; the 25% fraction is not multiplied into a free-capacity grant. Installed capacity and soft penalised stock exceedance remain distinct. No aggregate investment budget exists in the current contract.

See `docs/workbook_review_and_adjustment_plan_20261124.md` and its sanitised evidence for all six workbook questions and the proposed next-version adjustment sequence. The reviewed XLSX files are not changed. Their active interface should remove obsolete approval/default-penalty text while immutable technical provenance remains preserved. Proposed changes need subsequent author approval before workbook generation.

The separately requested package upper-bound change is isolated in Draft PR165. Installed editable metadata is not refreshed: no shared or base environment changes are authorised. PR159 remains unchanged and Draft. No new job, optimizer run or merge occurred.
