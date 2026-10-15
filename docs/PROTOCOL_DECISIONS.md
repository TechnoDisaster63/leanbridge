# Decisions the user must make before any confirmatory lab run (none are made here)
1. H1 vs PASS rule: source H1 requires >=90% throughput retention; the v8 section 8 PASS rule is CI-only. Which governs? (Unresolved since the first QC.)
2. Latency metric: "penalized p99" is undefined. Choose the definition (e.g. p99 or p95 of loaded RTT during load, how unfinished/lost probes are penalized).
3. Throughput reference: retention vs which arm (unshaped, static CAKE at initial capacity, or retuned static)? Unshaped favors never shaping; retuned static in the toy sim traded retention (0.60-0.75) for p99 0.
4. Trials: screening ~10, confirmatory >=30 per scenario (proposed), CI method, and what counts as an exclusion.
5. Scenarios and ISP buffer size/AQM-free bottleneck settings for the emulated link; cross-traffic model (bursts defeated every toy arm).
6. KILL rule: the old rule (no arm beats static CAKE after two design iterations) vs the new baselines (retuned static, cake-autorate); toy results are NOT a KILL or PASS.
7. Scope: this plan assumes an emulated link inside a disposable VM. If the user means a real physical or live-ISP test, say so; that is a different, higher-risk plan and is not authorized here.
8. Disposable VM host/hypervisor, isolation and resources must be verified before lab execution. No router or hardware purchase is part of the offline workflow.
