# Audited read-only installed envelope — PR63

Source `7532beea7ffa429ba9f34bfd091bd60069efc4f8`; integrated by PR #63 at
`0dccbfd5d25c4db97a74baf5da3766d7433c82a1`.
Original portable archive: `s2-envelope-evidence.tar.gz`, SHA-256
`e86c703eb59336230ed9c3af6efc4fd602f9acf2b702ddbbb4553c650346b45a`.
The strict read-only auditor accepted its exact two-member set and recomputed
review. These JSON files preserve the original decoded records with readable
formatting; they are not the original archive bytes. Canonical receipt digest:
`b81b4490a74cd1bcc7695dbd5c7e70ffa72fbccc30f5ddebbf3655bda2cde751`.

Outcome: **observed_not_admitted**. Installed clients report Slurm 22.05.11;
selected declared settings match the earlier inventory. Binary/source identities
were recorded. This is not daemon attestation, installed job/step grammar
qualification, live isolation, a synthetic execution or S2 completion.
The maintainer reports 169 passing tests and one intentional non-Linux-only
negative-CLI skip, driver exit zero and preserved run. The regression XML and
private path-bearing envelope were not transferred: those claims are not
independently recounted here. The original failed PR62 bootstrap remains in
the checkpoint and recovery runbook; it is not replaced by this success.

No license, raw configuration, private envelope, local location receipt or
unrelated context is committed. Subsequent code gets a fresh source identity;
this archived source/digest must never be relabelled as a later revision.
