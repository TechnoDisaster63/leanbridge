# lab/ provenance

This file records where the lab files came from. Hashes identify bytes. They are not approval.

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
