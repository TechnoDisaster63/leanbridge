# Security and safe handling

LeanBridge is a public research prototype (MIT License) with no live network executor. It is not supported for production or use on a primary host network.

## Reporting a concern

Report a suspected issue privately to the repository owner through an existing trusted contact route. Do not post secrets, packet captures, host addresses or exploit details in a public issue. A dedicated security mailbox or response-time commitment has not been set up.

Include the affected source revision, a minimal sanitized input, expected behavior and actual behavior. An offline reproduction is preferred. Do not test on someone else's network to demonstrate a bug.

## Boundaries

- Do not execute dry-run command arguments.
- Do not run the core prototype or dry-run tooling with root privileges.
- `lab/cake_netns_lab.py` performs privileged network-namespace and traffic-control operations. It is a separate **UNTESTED and NOT CLEARED** draft; do not run its preflight or any lab arm until the exact revision has been independently reviewed and explicit clearance recorded.
- Licensing, passing core or mocked lab tests, a disposable VM and a static source read-through do not constitute execution clearance.
- Any later authorized lab run must follow the documented disposable-VM and network-isolation requirements. Virtual-machine detection alone does not establish isolation.
- Do not add API keys, passwords or private captures to the repository.
- `.gitignore` prevents some accidental tracking; it does not remove previously tracked secrets or scan history.
- Tests are not a security audit. The parser, identity and execution boundaries in the [open review](docs/REVIEW_v0.4_OPEN.md) are unresolved.
- Public availability or an MIT license does not make private data safe to commit, redistribute, or retain.

No supported production version, vulnerability bounty or disclosure schedule is claimed.
