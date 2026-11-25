# Comprehensive extra_4 report PDF

Date: 2026-11-24. Presentation export, not the W18 preservation round.

The user requested a PDF of the existing comprehensive report. [Detailed PDF](../../../outputs/extra4-detailed-report-v1/extra4-comprehensive-report.pdf) converts W17 presentation revision02 into a printable report with all 186 cluster decisions/reasons, per-shank accounting, the release raster and an embedded appendix of all 48 linked historical waveform images. The 186 waveform links target internal PDF destinations. Historical captions and reasons remain historical; current decisions take precedence. Local data-download links become labels rather than broken file links. Interactive filtering and event-level datasets are not embedded; the corrected workbook remains in the separate team-sharing package.

The builder `scripts/build_extra4_detailed_pdf.py` verifies frozen release and presentation manifests, parses report content, preserves reason text and embeds original images without scientific changes. All 186 reasons were verified in extracted PDF text; 186 links reach 48 distinct internal destinations. Rendered pages were visually inspected, with layout corrections for tables and section flow. Scientific acceptance, held-cluster status, source artifacts and the eight-page sharing summary remain unchanged.

The generated PDF and checks are hashed in its output manifest. Tracked `configs/extra4_detailed_pdf.v1.json` pins the builder, source manifest and deliverable. W18 preservation/handoff remains next after review. No commit or push performed.
