# Final submission — NorthStar Property Investment Consulting

**Team 5 · Ashish Nath · Justin Kretschman** — BUKD-X500 Agentic AI Systems, Design Studio

| File | What it is |
|---|---|
| `NorthStar-WriteUp.docx` | The 5-page write-up (editable) |
| `NorthStar-WriteUp.pdf` | Same document, ready to submit |
| `NorthStar-Presentation.pptx` | 7-slide deck for the 5-minute pitch, with speaker notes and timings |

Screenshots used in the write-up live in `../screenshots/`, captured against the
running app rather than mocked up.

## Regenerating

Both documents are generated from scripts so their figures track the repository —
a deck claiming a test count the suite does not have is the kind of error that
undermines a demo. After changing the project, re-run:

```bash
python scripts/build_writeup.py
python scripts/build_presentation.py
```

Figures live at the top of each script (test count, ZIP count, note count). Edit
them there, not in Word or PowerPoint, or the next regeneration will overwrite
your change.

To refresh the screenshots, start the app and re-run the capture steps described
in `scripts/build_writeup.py`.
