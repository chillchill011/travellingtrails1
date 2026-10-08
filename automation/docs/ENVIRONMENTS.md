# Travelling Trails Environment Identity

> **Hard safety boundary. Do not infer environment from Netlify's `context: production` label.**

| Environment | Git branch | Netlify project | Site ID | Canonical URL |
|---|---|---|---|---|
| STAGING | `Staging` | `devtravtes` | `bb8c325b-9562-4952-8613-439ca95dc9e0` | `https://devtravtes.netlify.app/` |
| PRODUCTION | `main` | `travellingtrails1` | `edd2477f-24f5-4005-a05c-f0310f1efe11` | `https://travellingtrails.in/` |

Automation writes and review handoff target **Staging only**. Production promotion remains a separate manually approved phase.

The historical planning documents that say automated GitHub writes target `main` predate the implemented staging-first architecture and are not operational instructions.
