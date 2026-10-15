# Isolated lab design

**Proposed, not executed.** Goal: compare LeanBridge with real `tc`/CAKE baselines on an emulated link inside a disposable Linux VM. This is not a live-ISP test, a host-network test or permission to buy hardware. Toy results do not validate this design.

## Mechanism references

These references describe existing tools, not LeanBridge performance:

- [tc-cake manual](https://man7.org/linux/man-pages/man8/tc-cake.8.html): CAKE shaping parameters.
- [cake-autorate project](https://github.com/lynxthecat/cake-autorate/blob/master/README.md): adaptive CAKE-rate control. Its development branch is not a stability guarantee.

For an offline lab comparison, reflectors must be inside the lab. Results apply to that configuration, not internet reflectors or physical appliances.

## Proposed topology

```text
ns_client -- veth -- ns_box -- veth -- ns_isp -- veth -- ns_server
                    CAKE             emulated rate/buffer
```

One disposable VM can contain these namespaces. This is a design choice, not a guarantee that any laptop has enough CPU, memory, storage or timing stability.

- Preserve the original VM; use a disposable full clone and a clean powered-off snapshot.
- During isolated runs, disable all external VM adapters or use Not attached. Host-only still permits host contact and is not full isolation. Do not use bridged access, shared folders, shared clipboard or USB passthrough for the lab.
- Any temporary package-setup connectivity is a separate preparation phase and must be removed before isolated runs.
- Future privileged network changes belong only inside that verified VM and named namespaces, never the host or physical NICs. No such changes are authorized by this document.
- Emulated capacity events and buffer size must be frozen in the manifest; they strongly affect results.
- Kernel CAKE support and timing stability under load remain unverified. Loading a module or adding a qdisc changes state and is not a read-only check.

## Comparison arms

A: no shaper. B: static CAKE at initial capacity. C: static CAKE retuned to post-drop capacity, labeled oracle-like. D: cake-autorate default. E: cake-autorate tuned on separate data. F: LeanBridge, once a reviewed adapter exists. Include declared ablations of F.

The in-repo static/AIMD arms are toy stand-ins, not real CAKE or cake-autorate comparisons.

## Staging

1. **Offline parsers, implemented:** supplied qdisc JSON and netdev text; hand-built fixtures only.
2. **Offline dry run, implemented:** supplied observations produce argument lists with `executed=False`; no real collector or kernel binding.
3. **Read-only VM collection, not implemented:** capture verified, namespace-bound telemetry and real RTT probes, including an idle baseline and lost/late rules.
4. **Reviewed executor, not implemented:** namespace/device identity, verified VM marker, bounded rate conversion, option preservation, exception holds, emergency stop and tested rollback.

Each new boundary needs independent review before progressing. The offline-only review does not authorize stages 3 or 4. CAKE tin delay is sojourn time, not upstream queue delay or RTT.

## Proposed additional lab gates

These L1-L8 gates do **not** replace the original seven open gates, whose itemized record remains unavailable.

| Gate | Required evidence | State |
| --- | --- | --- |
| L1 | Disposable snapshot; external adapters and sharing disabled during runs | Open |
| L2 | Namespace/device binding and verified VM marker; rejection outside scope | Open |
| L3 | Fault injection cannot bypass the guard or safe hold behavior | Open |
| L4 | Real-kernel fixture capture, verified units and malformed/missing input tests | Open |
| L5 | Idempotent rollback/teardown restores initial state without unsafe temporary state | Open |
| L6 | Independent review of the collector, probes, executor and rollback | Open |
| L7 | Frozen arms, scenarios, seeds, metrics and exclusions before confirmation | Open |
| L8 | Explicit clearance for the exact isolated run | Open |

[Open review](REVIEW_v0.4_OPEN.md) · [Safety](SAFETY.md) · [Protocol decisions](PROTOCOL_DECISIONS.md)
