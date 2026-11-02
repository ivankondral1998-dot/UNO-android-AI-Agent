# O01–O08: decisions still RESERVED FOR OWNER

No recommendation below equals approval. Do not silently lock a choice while editing docs.

| ID | Choice | Candidate recommendation (NOT approved) | Evidence required |
|---|---|---|---|
| O01 | WAKE/SENSOR required vs optional/frozen | Required as desired full organism | acoustic/freshness metrics, device test |
| O02 | cyclic-prefix vs arbitrary masks | cyclic-prefix baseline and arbitrary comparator | quality vs energy |
| O03 | B2 model widths / LR2 / H2 | test B2 512,1024,1536; 2048 control; fallback by failure trigger | trained weights, locked evaluation |
| O04 | exact memory ABI | separate semantic summary + RetrieveExact | conflict/revoke/TTL/fault injection |
| O05 | strict local offline/SAF | app-private or verified-local only by default | zero-network behavior incl providers |
| O06 | quality/coverage/security thresholds | predefine per-class q_j,c_j,r_j BEFORE locked tests | datasets/oracles, not post-hoc thresholds |
| O07 | Android authority boundary | external controller & consent, not legacy OwnerGate | enrollment, session, cancel, overlay threats |
| O08 | decision policy for architecture/resources | choose quality-feasible, then measured joules per verified task | actual A52 measurements |

Never fabricate the owner's signatures. Owner approval has NOT occurred. After owner approves each choice, link to exact approval record and timestamp and update this table on a separately authorized branch. Approval of G4 and permission to write production code are **separate acts**.
