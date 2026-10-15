# Safety contract
1. No live-network or host execution until the adapter is independently reviewed, the seven safety gates
   are closed, and documented clearance is granted. A simulator pass is not proof of real-network safety.
2. Guard has final authority: hard min/max, upward step limit, probe lockout after congestion.
3. Fail closed: invalid/stale/missing telemetry never raises the rate; after N misses rate drops to the fallback.
4. Same saved inputs + config reproduce the same decisions (tested).
5. LLM: read-only explanation of approved logs; no shell, no shaping access.
6. Scratch rebuild: no code reused from earlier harness scripts that failed review.
Seven gates: the list lives in the v8 source document and is not reproduced here; map them to tests in phase 3.
