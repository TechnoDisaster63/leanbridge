# lab/ provenance (reviewed draft, NOT validated)

- Repo core pinned: commit 7c49d55f2e45da039bd818e6e0beafe5443253ea (src/ unchanged by this addition; lab loads it from a root-owned copy).
- Files and SHA-256 at upload:
  85589ac9a610f7619e512c6b74392326a6c06c67090582bc76ea9ab7c750a2bb  cake_netns_lab.py
  98b3a474128c6c3145e8a54d80d0be920402b78bd85f1ef3da04a0445262d9fd  test_cake_netns_lab.py
  3898bb2e1f2598b25a26756a891c7f1d6713caa79550b27604527584043d10cb  README_LAB.md
- Tests: 42 unprivileged mock tests (python3 test_cake_netns_lab.py), not kernel validation.
- Status: static independent review found no code blockers; never run as root or against a kernel. No results exist.
- Not implemented: physical phone or laptop in the data path. All endpoints are namespaces inside one VM.
