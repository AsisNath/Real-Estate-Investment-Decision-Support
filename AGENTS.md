Project Memory File:
Create and maintain a root-level file named agentic.md.

Purpose:
agentic.md should act as the AI project memory so that if development stops and resumes later, the AI can quickly understand the project status, decisions, architecture, assumptions, and next steps.

Requirements:
1. At the start of every work session, read agentic.md first if it exists.
2. If agentic.md does not exist, create it.
3. Keep the file concise but useful.
4. Update agentic.md after major changes, especially when:
   - Project structure changes
   - Architecture decisions are made
   - APIs, data files, or assumptions are added
   - Financial formulas are implemented or changed
   - Bugs are found or fixed
   - Tests are added
   - Work is incomplete and needs to resume later

agentic.md should include these sections:

# NorthStar Property Investment Consulting - AI Project Memory

## Project Goal
Brief description of what the app does.

## Current Architecture
Summary of frontend, backend, data files, financial model, and data flow.

## Key Decisions
Important choices made during development and why.

## Data Assumptions
What data is real, sample, mocked, public, user-provided, or unavailable.

## Financial Model Notes
Summary of formulas and calculation rules.

## Current Status
What is already working.

## Known Issues
Bugs, limitations, missing pieces, or uncertain parts.

## Next Steps
Clear checklist of what to do next.

## Run Instructions
How to run and test the app locally.

The AI should treat agentic.md as the source of continuity for the project. It should not store private secrets, API keys, passwords, or sensitive personal information in this file.