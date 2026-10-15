# LeanBridge real-packet lab: UNTESTED DRAFT, NOT CLEARED

STOP: do not run steps A-D until you are told this exact version has been independently reviewed and cleared.
Status: no kernel run has happened. No results exist. Kernel behavior is unverified.

What it does: four new network namespaces inside ONE Linux VM (client, LeanBridge router, ISP router, server) joined by veth.
Real kernel TCP (iperf3) and ping cross a CAKE qdisc on the LeanBridge router and a tc-tbf bottleneck that changes 20 -> 6 -> 20 Mbit.
One arm per run: none (fifo), static (CAKE 18 Mbit), heuristic, leanbridge (repo controller, 1 s steps).
It does NOT put your phone or laptop in the path, touches no host interface, and does not use your real internet.

The script cannot verify that your VM is disposable, snapshotted or isolated. --i-confirm-disposable-vm is only your statement.
Before any root step you must have: a fresh snapshot; all VM network adapters disabled or not attached during the test (the lab needs no network; install iperf3 beforehand, then detach; NAT is only for a separate, agreed dependency step and must be turned off again; host-only still reaches the host and is not isolation); no shared folders or
shared clipboard to the host; nothing you need stored in the VM. Hyper-V/WSL and containers are refused. VirtualBox, KVM, VMware, Xen are accepted.
Needs: root, kernel with sch_cake and sch_tbf, iperf3, iproute2.

Safe now (no root):
  cd lab && python3 test_cake_netns_lab.py     # 42 mock tests, no namespaces (NOT with -I: the test imports the local script)
  python3 -I lab/cake_netns_lab.py --plan --arm leanbridge     # prints commands only (run from repo root)

After clearance only:
  A. (from the repo root) sudo mkdir -p /opt/leanbridge-lab && sudo cp -r lab/cake_netns_lab.py src /opt/leanbridge-lab/ && sudo chown -R root:root /opt/leanbridge-lab && sudo chmod -R go-w /opt/leanbridge-lab
  B. sudo python3 -I /opt/leanbridge-lab/cake_netns_lab.py --check --i-confirm-disposable-vm      # creates and deletes a throwaway namespace
  C. sudo python3 -I /opt/leanbridge-lab/cake_netns_lab.py --execute --i-confirm-disposable-vm --code-dir /opt/leanbridge-lab --arm none
     (then static, heuristic, leanbridge; one per run). Each run takes about 45 s plus setup.
  D. Interrupted run: sudo python3 -I /opt/leanbridge-lab/cake_netns_lab.py --cleanup --run-id <id printed at start>
Send back: the full terminal text and the final JSON line of each run. Single samples, not a benchmark.
Unknown until first run: sch_cake present, tc JSON bandwidth units (bytes/s assumed, mismatch aborts), ping -O output format, iperf3 JSON, timing, SIGHUP over ssh.
