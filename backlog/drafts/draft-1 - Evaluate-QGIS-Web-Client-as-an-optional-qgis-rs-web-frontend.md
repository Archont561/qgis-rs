---
id: DRAFT-1
title: Evaluate QGIS Web Client as an optional qgis-rs web frontend
status: Draft
assignee: []
created_date: '2026-10-07 14:30'
labels: []
dependencies: []
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Explore whether QGIS Web Client (QWC2) is a suitable optional browser frontend for qgis-rs HTTP services.

Keep product boundaries explicit: qgis-cli remains the process CLI and orchestration surface; qgis-server owns HTTP/OGC endpoints; any browser frontend is a separate, independently deployable client rather than a qgis-cli dependency or bundled application.

First map QWC2 expected QGIS Server services and configuration/authentication to qgis-server intended surface (WMS, WFS, XYZ tiles, OGC API Features). qgis-server currently has route definitions but its HTTP listener is unimplemented, so this draft does not assume drop-in compatibility or schedule frontend implementation before the backend is functional.

Deliver a recommendation between QWC2 compatibility and a lighter custom web client, with identified endpoint/configuration gaps and a minimal end-to-end proof against a real project and qgis-server. If QWC2 is selected, keep it optional and separately deployable.
<!-- SECTION:DESCRIPTION:END -->
