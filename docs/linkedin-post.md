# LinkedIn launch post

## Suggested post

I’m excited to share **GhostTrace** — an evidence-first deletion auditing agent I built for the HackerRank Orchestrate challenge.

The problem sounds simple: delete a customer’s account.

In a real distributed system, personal data can remain in:

- database replicas
- search indexes
- analytics systems
- support attachments
- exports and logs
- backups
- active synchronization pipelines

GhostTrace checks whether the data is truly gone instead of trusting a workflow status such as “Complete.”

### How it works

1. Resolves current and historical customer identifiers.
2. Reads structured and multimodal evidence.
3. Reconstructs the state at the audit timestamp.
4. Applies retention and deletion rules.
5. Detects active sync and restore risks.
6. Produces ordered findings, remediation steps, and verification checks.

The core engine is deterministic and evidence-first. Optional AI assistance is isolated to ambiguous intent and image extraction; it does not invent evidence or control the final policy decisions.

### Results

The final pipeline generated and validated all **518 cases**.

On the public 32-case sample, it achieved:

- **96.88% status accuracy**
- **73.54% step F1**
- **100% authored regression-test accuracy**

The project taught me an important lesson: deletion is not a button. It is a system-wide proof obligation across identity, storage, replication, retention, and recovery paths.

GitHub: https://github.com/tanaygt/ghosttrace-deletion-audit

I’d love feedback from people working in privacy engineering, distributed systems, data governance, and AI evaluation.

#Python #AI #PrivacyEngineering #DataGovernance #DistributedSystems #CyberSecurity #SoftwareEngineering #HackerRank

## Beginner-friendly explanation

GhostTrace is like a detective for deleted customer data. It looks in every place where the data might still exist, checks old names and emails, finds systems that could recreate the data, and explains exactly what should happen next.

## Recommended screenshots

Attach two or three clean images:

1. **GitHub overview:** repository name, README title, and the `code/` and `docs/` folders visible. Crop out private paths and challenge data.
2. **Architecture:** use [`architecture.png`](architecture.png), showing the simple flow from request → identity history → evidence → policy → verification.
3. **Validation:** terminal output showing the 518-row run and validator pass. Do not show customer evidence, API keys, local usernames, or private trace files.

## Short version

Built GhostTrace, an evidence-first deletion audit agent for distributed customer data.

It resolves historical identities, checks databases, replicas, search, analytics, support, exports, logs, backups, and sync flows, then generates an ordered remediation and verification plan.

Final run: 518 validated cases. Public sample status accuracy: 96.88%.

GitHub: https://github.com/tanaygt/ghosttrace-deletion-audit

#Python #AI #PrivacyEngineering #DistributedSystems
