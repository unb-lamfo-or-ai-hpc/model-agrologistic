# T1 source-hash and dependency readback review — 23 November 2026

**Decision: accept the readback with coverage limits.** The finite selected scope
is complete. No source archiving, relocation or deletion is approved.

## Package integrity and continuation

| Collection | Archive SHA-256 | Internal manifest entries |
| --- | --- | ---: |
| First, partial: 3bb356281ac2 | 35caa71a5bad5d5b0eca6f48116dbc225f1b2f9bf19bdafecb908745bd258a63 | 8 |
| Second, cumulative: caaa456c51c4 | d6842db7a92974d1666aa4b0256c7db308db65b25e02660367c705288433956b | 11 |

Both sidecars, all manifest entries and safe archive-member checks pass.
The eight shared report files are byte-identical across collections.
The later collection contains the original first readback and the additional
second readback; do not add the cumulative packages as independent workloads.

The plan hash is
c15b488dd8283864a241b8b20d6bbcb07d48a2ceb7e282a767b52a9d6da402ab,
with executed source d3a0c654b1b20ae86ae1fbd0bf18992fdcc9cb41.
All three helper SHA-256s agree with the pinned handoff, and the plan's
classification CSV hash matches the locally audited T1 classification.
The original reader/launcher code and all receipts remain unchanged.

[Machine-readable evidence](evidence/npad_t1_hashdeps_readback_20261123.json).

## Completion and guarded records

| Stage | Newly observed records | Stable hashes | Database guard |
| --- | ---: | ---: | ---: |
| First readback | 91685 | 91683 | 2 |
| Explicit continuation | 21619 | 21619 | 0 |
| Combined unique scope | 113304 | 113302 | 2 |

The combined scope matches 110707 archival/cache candidates plus 2597 retained
comparison files exactly. There are no repeated record IDs, missing selected
IDs or incomplete trailing journals. Hash-phase reads total 16,430,804,142 bytes.
Control-JSON dependency reads are an additional, separately scoped measurement.

The two guarded records total 31 bytes and occur under recorded test-fixture paths.
Their filenames end in cache.sqlite3, so the conservative database rule excluded
their content from hashing. Their actual file format was not inspected.
Neither is the active 212803584-byte OSRM cache. The two guards are preserved
outcomes, not a hash failure or proof that the production database was qualified.

All 338 cache-deletion candidates and 2597 retained comparisons have stable
hash records. Of 110369 archival proposals, 110367 were stable and two were guarded.
Stable means the reader's before/after identity and mutation checks passed at
observation time; this is not a whole-filesystem snapshot or an external reference
comparison.

## Content identity now observed

There are **4087 nonempty matching-content groups**, spanning 89455 path records,
with at least two distinct observed inodes per group. Their logical excess over
one observed inode per group is 3,376,348,759bytes (approximately
3.1445 GiB). This is not an approved reclaimable amount,
a compression forecast or a complete-project deduplication estimate.
The hashed scope also includes 1737 empty-file records, retained separately.

Examples of matching payloads include source/registry snapshots, historical
gold workbooks, solver-distribution tarballs, figures and original flow/inventory
exports. 1136 groups contain both retained active-comparison and archival-proposal
records. Stable content equality is stronger evidence than the initial name/size
hints, but each scientific observation still retains its own source, configuration,
receipt and validation identity.

A verified archive or future content-addressed layout must preserve these
relationships and support full restoration. Matching bytes do not justify
removing an original claim or its absolute-source dependencies.

## Dependency evidence: separate specific from broad references

Both captured queue queries succeeded and returned no user jobs at their
respective observation times. Each snapshot read 9606 control JSONs and 2214
symlink references. It also records 14 omitted control JSONs and 18 unreadable
process entries; other users, remote nodes, containers and closed dependencies
remain incompletely observable. The omission counts have no per-file reason list
in the original reader output and need targeted clarification before they can
support a specific cleanup decision.

The original prefix flag treated a shell's cwd at the audit root as a possible
reference to every child. That flag is deliberately conservative; a root cwd
does not establish that all child files are being consumed. Offline refinement
separates observed reference types without rewriting the original receipts:

| Selected class | Exact file reference | Specific directory reference | Broad root cwd only | No reference observed in partial scope |
| --- | ---: | ---: | ---: | ---: |
| Archival proposal | 151 | 54517 | 52111 | 3590 |
| Cache candidate | 0 | 104 | 160 | 74 |
| Retained comparison | 36 | 2029 | 215 | 317 |

These are reference categories, not live-use certificates. Exact and directory
references may be declared in historical controls or symlink metadata rather
than observed open file descriptors. Absence of a reference is not clearance.

## Updated custody recommendation

1. Preserve active inputs, OSRM provenance/cache, Gurobi 14 review evidence and
   consumed-claim safeguards. The two new local XLSX files remain working review
   copies pending researcher revision; this hash pass does not finalize MVP3 data.
2. Retain historical evidence for a concrete archival design. Prioritize the
   largest complete campaign bundles, keeping source/input/validation/receipt
   relationships and checking external custody plus restoration.
3. Keep all 338 cache candidates conditional. 74 have no observed reference in
   the limited snapshots; 104 have a specific directory reference and 160 only
   a broad root-cwd flag. Their total logical size remains about 1.7643 MiB.
4. Treat the 3.1445 GiB matching-content excess as a consolidation research list.
   No source path is approved for unlinking, deduplication or moving.
5. If further dependency resolution is needed, inspect the 14 omitted controls
   with a targeted read-only diagnostic. There is no reason to repeat the
   completed 113304-record hash pass.

The full private file/group/dependency tables are delivered locally.
GitHub receives redacted counts, provenance and this assessment only.
PR #159 and PR #163 remain Draft. No new job, solver, shared-environment change,
manuscript edit, source-data compression, cleanup or merge is performed.
