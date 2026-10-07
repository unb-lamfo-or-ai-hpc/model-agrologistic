# S1-B h400 direct-enabled input inspection: accepted terminal evidence

## Disposition and provenance

The single input-only job **2200298** is accepted. It completed on NPAD and the
original collector/reviewer accepted its receipts. A separate local execution of
the same portable reviewer accepted the transferred archive after checking its
SHA-256 against both the adjacent checksum and the user-reported digest. This
closes the input-inspection scope of PR #50, **not the h400 solve or all of S1-B**.

- Experimental source: `de8c9a138526f63883cc2672077fbee4d38c8c60`.
- Develop base: PR #49 merge `98658f501a67da83197c67add1da9bf884568e46`.
- Archive: `h400-input-evidence-2200298.tar.gz`.
- Archive SHA-256:
  `d668f35cff87dcfd7f90c03a14d7b332571e581821ee5a90b80b2ab52e67b8e3`.
- Preserved run:
  `/home/vrrcelestino/model-agrologistic-hygiene-audit/mvp2-h400-input-s1b-h4g2KNoc`.
- Preserved collection:
  `collection-3c7LbB9x/evidence`, inside that run.
- Original qualified miniature source:
  `f9aa74abecfe416bac9f505b55c4eeacf4b111be`.
- Reference manifest SHA-256:
  `348c4c08c2c9e906cbd3a28df7753577ebed3cac30702aae30dfb8ce2ad25694`.
- Qualification report SHA-256:
  `b9e4b2a5bb7ecf66b0c54432986c3033bf381bdea223fc914ddefa7dcc24bde7`.
- Workbook SHA-256:
  `c3085456997714ef5a8bdbf61e2c9a5e578c2636003947427cf58933d21ceb13`.

The archived scheduler, plan, worker, diagnostic and six input-product receipts
agree. The 19 regular allowlisted archive members total 194,173 expanded bytes;
the portable reviewer checks safe names, bounded expansion, catalog/member
hashes, tool/policy/core identities, serialized single-control contract and
reconstructed input semantics. Original identities were checked on NPAD before
and after loading. No credentials, workbook bytes or whole checkout were
transferred or published as this report.

## Observed input contract

| Item | Accepted observation |
| --- | --- |
| Hubs | 400: 146 existing, 254 candidate |
| Origins / customers | 37 / 27 domestic plus ten export |
| Products / scenarios / periods | Two / nine / sixty |
| OD / DC / DD / OC routes | 5,920 / 6,400 / 64,000 / 592 |
| Repair routes | Zero in all four families |
| Potential interhub connectivity | Strongly connected for Milho and Soja |
| Selected interhub edges per product | 32,000, one strong component each |
| Input model audit | Zero errors, warnings and informational findings |
| Loader warnings | Two, retained in the data signature |
| Estimated variables | 42,426,624 |
| Flow variables | 41,532,480 |
| Inventory / emergency variables | 432,000 / 432,000 |
| Investment / unmet-demand variables | 984 / 29,160 |

The input model audit and loader diagnostics are distinct: an empty finding list
in the former does not erase the two loader warnings. Potential connectivity is
not active-network connectivity, throughput feasibility or a proof of complete
recourse. No solution exists here, so no solution residual validator was run.

The solver size guard remains **25,000,000**. The receipt explicitly reports
`within_reference_limit=false`, excess **17,426,624**, and
`optimization_allowed=false`. These are estimates from loaded inputs, not an
actual solver matrix. Neither a generic guard relaxation nor a solve exception
was introduced. All prior warehouse-only h215/h300 gates remain unchanged.

## Terminal execution and limits of interpretation

The exact root job, batch and extern steps report `COMPLETED`, `0:0`, and
`00:03:00`. Worker and diagnostics close at phase `complete`; the worker records
`optimization_executed=false`. The earlier sbatch test-only message `2200297`
was not the submitted input job.

Observed allocation: standalone job on **r1i3n4**, partition **intel-256**, one
node and one task, four allocated CPUs / four CPUs per task, **16,384 MiB**,
thirty-minute time limit, effective QOS **preempt**, and no restarts in the
captured running scheduler record. No exclusive-node claim is made.

Slurm reports batch MaxRSS **271,204 KiB** (about **264.85 MiB**, **0.259 GiB**);
extern MaxRSS is 928 KiB. This measures only this batch's input inspection. It is
not native solver memory, a solve peak, a resource-savings comparison or evidence
that h400 can be optimized within 16 GiB. The three-minute batch duration is not
an optimization runtime. No solver model was built, no fresh license probe was
performed and no optimization was executed.

NPAD pre-submit focused regression passed **181 tests in 23.84 s**, with zero
failures/errors/skips. The experimental source passed all three Linux PR checks.
The unchanged core source hashes replay locally. Original NPAD runtime receipts
retain Python 3.13.15, Gurobi 13.0.3, PySCIPOpt 6.2.1, NumPy 2.5.2,
pandas 2.3.3 and openpyxl 3.1.5; those original runtime values are not replaced
with the reviewer's local environment.

Portable review is independent of the original collection execution, but it is
a **receipt/semantic replay**, not independent reloading of absent private
workbooks or original qualification artifacts. Those files were rehashed on
NPAD; they cannot be rehashed locally from data not included in the archive.

## Integration and next boundary

After this report is published, unchanged experimental blobs are verified and
final-head CI passes, PR #50 can be marked Ready for review and separate merge
authorization requested. The original run and global claim must remain intact;
collection does not admit a repeat.

After accepted input evidence is integrated, a **separate S1-B solve-admission
PR** must qualify one instrumented h400 direct-enabled control: exact size
exception, finite allocation/cgroup/license gates, immutable inputs/source,
bounded execution, complete three-stage hierarchy, independent solution
validation and terminal telemetry. A retained partial incumbent is not a
completed hierarchy. If defensible resource admission is unavailable, record
that limit rather than launch a campaign.

S1-C follows with Sprint 1 evidence/exit reconciliation; thread screening remains
S2. No formulation, manuscript, frozen MVP1, compaction default or EVPI/VSS
editorial change occurs here; the latter remains deferred to S6. See the
[input-only protocol](mvp2_h400_input_preflight.md) for lifecycle and scope.
