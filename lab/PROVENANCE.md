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

The original no-run/no-results statements above describe the earlier upload, not the later completed session. The owner subsequently supplied four real-packet VM run transcripts using the original script and pinned src. See the [separate session record on main](https://github.com/TechnoDisaster63/leanbridge/blob/main/docs/VM_LAB_2026-10-16.md) for results and limits. All loss fields are invalid; the reporting bug remains unfixed. No standing permission for another root run, general safety approval or physical-network deployment follows.
