# Security and safe handling

LeanBridge is a private research prototype with no live network executor. The `lab/` directory holds an untested, never-run, NOT cleared draft lab script; see the boundary below. It is not supported for production or use on a primary host network.

## Reporting a concern

Report a suspected issue privately to the repository owner through an existing trusted contact route. Do not post secrets, packet captures, host addresses or exploit details in a public issue. A dedicated security mailbox or response-time commitment has not been set up.

Include the affected source revision, a minimal sanitized input, expected behavior and actual behavior. An offline reproduction is preferred. Do not test on someone else's network to demonstrate a bug.

## Boundaries

- Do not execute dry-run command arguments.
- Do not run this project with root privileges. The only possible exception is `lab/cake_netns_lab.py`, and only after a separate, recorded clearance for that run, inside a disposable snapshotted VM with all network adapters detached (see [lab/README_LAB.md](lab/README_LAB.md)). That script's self-attestation flag cannot verify those conditions. Everything else stays non-root.
- Do not add API keys, passwords or private captures to the repository.
- `.gitignore` prevents some accidental tracking; it does not remove previously tracked secrets or scan history.
- Tests are not a security audit. The parser, identity and execution boundaries in the [open review](docs/REVIEW_v0.4_OPEN.md) are unresolved.
- Repository privacy does not authorize redistribution or make uploaded data safe to retain.

No supported production version, vulnerability bounty or disclosure schedule is claimed.
