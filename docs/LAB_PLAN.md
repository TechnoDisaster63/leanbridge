# Isolated lab plan (PROPOSED, nothing here has been run)
Goal: measure LeanBridge against real tc/CAKE baselines on an EMULATED link inside a disposable VM. Not the user's
laptop network, not the home ISP link, no hardware purchase. Toy-simulator results are not evidence for any of this.

## Sources (mechanism only; none supports LeanBridge performance)
- tc-cake(8): https://man7.org/linux/man-pages/man8/tc-cake.8.html (CAKE has a `bandwidth` parameter; "autorate-ingress" is a
  separate estimator; shaper rate is otherwise static).
- cake-autorate README: https://github.com/lynxthecat/cake-autorate/blob/master/README.md (adjusts CAKE rates from load and ping
  response from reflectors; supports OpenWrt, Asus Merlin, and Debian-family OSes; master branch is "development, not guaranteed stable").
  Consequence: in the lab its reflectors must be a host INSIDE the lab (not internet hosts), and results are for that configuration.
- Earlier fetched, unrelated to this step: RAUC checklist, OpenWrt buildsystem, CM4 datasheet, Red Hat eBPF article.

## Topology (single disposable VM, network namespaces, no physical NIC)
    ns_client --veth-- ns_box (LeanBridge/CAKE point) --veth-- ns_isp (emulated bottleneck: tbf/netem rate + buffer) --veth-- ns_server
- VM on the user's native Kali via libvirt/QEMU or VirtualBox with NO bridged adapter and no shared folders during tests; take a snapshot first.
  Suggested 4 vCPU, 4-6 GB RAM (user has 16 GB). All tc commands run as root INSIDE the VM, only on veth devices inside named namespaces.
- Capacity events (50 -> 25 Mbps etc.) are produced by changing the ns_isp rate; the "ISP" buffer size is a documented lab parameter and
  strongly drives results, so it must be fixed in the manifest.
- Cannot be verified here: that the VM's kernel has sch_cake (check `modprobe sch_cake`/`tc qdisc add ... cake` inside the VM first) and that namespace timing is stable under load.

## Arms (real tools only for a real comparison)
A none | B static CAKE at initial capacity | C static CAKE retuned to the post-drop capacity (oracle-ish) | D cake-autorate default |
E cake-autorate tuned (tuning on separate seeds/runs) | F LeanBridge (needs adapter) | ablations of F (e.g. no change-point hazard, no probing).
The in-repo AIMD/static arms are toy stand-ins and must not be called baselines in lab results.

## Adapter staging (software, in this repo, each stage independently reviewed before the next)
1. Read-only telemetry: parse `tc -s -j qdisc show` and interface byte counters inside ns_box. No writes.
2. Dry-run controller: reads the telemetry, logs the `tc qdisc change` it WOULD issue. Executes nothing.
3. Gated executor: allowlist = {namespace names, veth names} defined in a config file; refuses anything else; refuses to run outside the VM
   (checks a marker file created in the VM); emergency stop = restore snapshot rate; rate bounds from SafetyGuard. Only after stage 1-2 review and documented clearance.

## Proposed lab gates (NEW and PROPOSED; they do not replace or close the earlier "seven open safety gates", whose list is unrecovered)
L1 VM is disposable, snapshotted, no bridged/NAT access to the laptop LAN during runs.   L2 Executor allowlist test passes (refuses host interfaces, refuses outside VM).
L3 Fault-injection tests show controller errors cannot bypass the guard.   L4 Telemetry parser tested on recorded tc output, including malformed input.
L5 Rollback/teardown restores the initial qdisc and namespaces; idempotent; no predictable /tmp state.   L6 Independent review of adapter code (earlier harness failed five audits).
L7 Manifest (arms, scenarios, seeds, metrics, exclusions) committed before confirmatory runs; tuning separated from confirmatory.   L8 Explicit user clearance recorded.

## Stage 1-2 status (implemented offline, reviewed? NO - pending independent review)
`tcstats.py` (parsers for `tc -s -j qdisc show` and /proc/net/dev, counter-rate helper) and `dryrun.py` (allowlisted command builder + planner that returns argv as data, executed=False).
No stage 3 executor exists. Test fixtures are HAND-BUILT from iproute2 field names (q_cake.c, tc_util.c, tc_qdisc.c), NOT captured real output; validate against real output inside the lab VM.
Known gap: CAKE's own tin delays (avg/peak_delay_us) measure sojourn time inside CAKE, not the upstream ISP queue that LeanBridge is meant to keep short. A real delay signal needs an active RTT probe (e.g. ping/fping/irtt to a lab host); that parser is NOT written yet.
