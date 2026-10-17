# lab/ provenance

This file records where the lab files came from. Hashes identify bytes. They are not approval.

## Original upload record - 2026-10-15 (historical)

- Repo core commit when these files were added: 7c49d55f2e45da039bd818e6e0beafe5443253ea (src/ not modified by this addition).
- SHA-256 of the lab files at upload (2026-10-15):
  85589ac9a610f7619e512c6b74392326a6c06c67090582bc76ea9ab7c750a2bb  cake_netns_lab.py
  98b3a474128c6c3145e8a54d80d0be920402b78bd85f1ef3da04a0445262d9fd  test_cake_netns_lab.py
  3898bb2e1f2598b25a26756a891c7f1d6713caa79550b27604527584043d10cb  README_LAB.md
- Tests: 42 mocked, unprivileged tests (python3 test_cake_netns_lab.py). They are not kernel validation.
- Review: on 2026-10-15 an independent reviewer did a dated, limited static read-through of the script and found no code blockers in that read. That is not a security audit, not kernel validation and not clearance to run.
- Never run as root or against a kernel. No results exist. Runtime unknowns remain: sch_cake availability, tc JSON units, ping output format, iperf3 JSON, timing, signal behavior over ssh.
- Run clearance: none recorded. A run needs separate recorded clearance.
- Not implemented: physical phone or laptop in the data path. All endpoints are namespaces inside one VM.

## Cwd-independent mock test - 2026-10-16

The owner supplied a ZIP of the pinned `ba5f97328f949a0ee41012a4abb5e62b48496ca5` checkout. Of its 46 files, 45 match that lab-branch tree byte for byte. The only local change is in `test_cake_netns_lab.py`: its subprocess script path now uses `os.path.join(L.HERE, 'cake_netns_lab.py')`, so the mock suite also works when launched from the repository root. The test imports `os`; `L.HERE` is a string. No script, controller or default changed.

- Updated test SHA-256: `f38a686161a7143bd1f9d668894e6a66db2b302583f77db03a238b31464be9b4`.
- Validation: 42 mocked tests passed in the owner's supplied Kali output and on the ZIP copy during reconciliation. These are not kernel tests.
- Original upload hashes above remain historical; script and README hashes are unchanged. The test file was not part of the privileged run copy.

The original no-run/no-results statements above describe the earlier upload, not the later completed session. The owner subsequently supplied four real-packet VM run transcripts using the original script and pinned src. See the [separate session record on main](https://github.com/TechnoDisaster63/leanbridge/blob/main/docs/VM_LAB_2026-10-16.md) for results and limits. All loss fields are invalid; the reporting bug was unfixed in that executed script (`ba5f9732`) and in the files at the time of this paragraph. A later, unexecuted fix is described in the next section; it does not change that historical record. No standing permission for another root run, general safety approval or physical-network deployment follows.

## Loss-accounting fix and recovery arm - 2026-10-16 (branch `lab-loss-fix`, NOT EXECUTED, NOT CLEARED)

Changes after the completed VM session, made offline with mocked tests only:

- **Loss accounting.** The executed script counted every `no answer yet for icmp_seq=N` marker as a lost packet and had no transmitted count, so its loss fields are invalid. The new `PingAccount` derives loss from sequence numbers (late replies count as received, repeated markers count once, the newest 6 sequences are treated as unresolved) and stops ping with SIGINT so ping prints its own summary, which is then authoritative. Output field `rtt_ms.loss` replaces `lost` / `loss_pct`. Tests include real `ping` summary parsing on loopback where ping works.
- **Recovery arms (HYPOTHESIS, unexecuted).** `--arm recovery` wraps the core controller with bounded upward probing and keeps the default guard (5% up-step cap). `--arm recovery_cap10` is an explicit opt-in that also raises the guard up-step cap to 10%, a safety-parameter change. They are separate arms because the offline model attributes most of the recovery gain to the cap, not the wrapper; see `docs/RECOVERY_v0.6.md` on the `overnight-v0.6` branch.
- The in-flight window is derived from the ping flags actually used (`ceil(wait / interval) + 1`, constants `PING_INTERVAL`/`PING_WAIT`, giving 6 for `-i 0.2 -W 1`). Existing arms (`none`, `static`, `heuristic`, `leanbridge`) are unchanged in behaviour apart from the loss fields. The executed pin `ba5f97328f949a0ee41012a4abb5e62b48496ca5` stays the only script that produced real results.
- Validation: 54 mocked tests pass (42 prior + 12 new; the recovery-module load test also needs the main-derived `src/` tree and was run there, 54 of 54). Not kernel validation. This script has never been run as root.
- New SHA-256: `cake_netns_lab.py` `5a51cc03d8a264a3d24ddb3c5d15714d6c7d744074d287b2f9bde29a00a43335`; `test_cake_netns_lab.py` `9d15eddd89dfce5fffb1c0b1248dd5cc4d961a04fcd3fae0977b2ea1b704957d` (hashes of the working copy at the time of writing).
- Any run of this version needs independent review of the exact version and explicit owner clearance for that run.

## One-command wrapper and vendored src - 2026-10-17 (branch `lab-oneshot-v0.7`, NOT EXECUTED, NOT CLEARED)

- `lab/run_lab.sh` chains the existing documented steps (fresh root-owned copy, `--check`, `--execute` per arm, `--cleanup`). It adds no network actions and keeps `python3 -I` and the `--i-confirm-disposable-vm` statement, which stays the owner's own unverified attestation. On interrupt it stops the lab, waits for it to exit, then runs `--cleanup` with the run id read from the current partial log (validated as 6 lowercase alphanumerics). The lab's exit status is kept (no pipeline masking it). It has never been run as root.
- `src/` on this branch is the `overnight-v0.7` source (adds recovery, pingloss, labmodel, accel modules; core controller, guard, estimator and config are unchanged from main). Fingerprint printed by the wrapper at start (sha256 of the sorted per-file sha256 list of `src/**/*.py`): `b7191b0386bb1a6cb46ae5da2ad5aef85a7283f31ed636865587db895d4c82c6`.
- SHA-256 at the time of writing: `lab/run_lab.sh` `31b704b7d50b095cfd7102794e234bc44c0cdad2ecb47ee2497d9334bc75bdd8`; `lab/test_run_lab.py` `496a1e77efa15d227313e1d0133b9661ba3bbc1aa661c1db1e64a78af775ad31`; `lab/cake_netns_lab.py` unchanged `5a51cc03d8a264a3d24ddb3c5d15714d6c7d744074d287b2f9bde29a00a43335`.
- Tests: 9 wrapper tests (refusals, arm list parity, exit status, run id validation, interrupt-then-cleanup ordering with a fake lab). They use no root and no namespaces; they do not test the real lab path.
- A run of this exact version needs independent review and explicit owner clearance.
