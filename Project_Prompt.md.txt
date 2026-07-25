Build a working local web application called “NorthStar Property Investment Consulting.”

Goal:
Create an interactive real estate investment decision-support website that runs locally on my PC. The user should enter a full mainland U.S. property address and basic investment assumptions. The app should return an investor-style report that analyzes financial performance, market context, local policy/rental risk, risks, opportunities, and a final recommendation.

Important:
This must be achievable as a class prototype. Do not depend on paid APIs. Do not require live real estate APIs for the first version. Use deterministic calculations for all financial numbers. Use mock/sample public-data records where live data is unavailable, but structure the app so real data APIs can be added later.

Project Type:
Local website / web app.

Recommended Stack:
- Backend: Python FastAPI
- Frontend: HTML, CSS, and vanilla JavaScript or simple React if already available
- Storage: local JSON files for sample market/policy data
- Financial model: Python module with pure functions
- Run locally at: http://localhost:8000

Core User Flow:
1. User opens the local website.
2. User enters:
   - Full property address
   - City
   - State
   - ZIP code
   - Purchase price
   - Expected monthly rent
   - Down payment percentage
   - Interest rate
   - Loan term
   - Property tax estimate
   - Insurance estimate
   - HOA fee
   - Maintenance percentage or monthly maintenance
   - Vacancy percentage
   - Property management percentage
   - Expected annual appreciation
   - Expected annual rent growth
   - Holding period: 5 years and 10 years
3. User clicks “Analyze Property.”
4. App generates a report with:
   - Property summary
   - Market snapshot
   - Rental policy / local restriction review
   - Financial analysis
   - 5-year and 10-year projections
   - Risk section
   - Opportunity section
   - Final recommendation: Buy, Investigate Further, or Reject

Architecture:
Use this project structure:

northstar-property-consulting/
  app/
    main.py
    finance.py
    analysis.py
    data_loader.py
    schemas.py
  data/
    market_data.json
    policy_data.json
    sample_properties.json
  static/
    styles.css
    app.js
  templates/
    index.html
  tests/
    test_finance.py
  README.md
  requirements.txt

Data Flow:
1. Frontend form collects property and investment assumptions.
2. Frontend sends JSON request to FastAPI endpoint:
   POST /api/analyze
3. Backend validates input using Pydantic schemas.
4. Backend sends numeric assumptions to finance.py.
5. finance.py calculates:
   - Loan amount
   - Monthly mortgage payment
   - Monthly operating expenses
   - Net operating income
   - Monthly cash flow
   - Annual cash flow
   - Cap rate
   - Cash-on-cash return
   - Break-even rent
   - DSCR
   - Estimated sale value after 5 years
   - Estimated sale value after 10 years
   - 5-year IRR
   - 10-year IRR
6. data_loader.py loads local JSON market and policy data by state and ZIP code.
7. analysis.py combines:
   - Financial metrics
   - Market data
   - Policy/rental restriction data
   - Missing data flags
   - Risk/opportunity rules
8. Backend returns one structured report JSON.
9. Frontend renders the report in a polished dashboard-style website.

Financial Logic:
All calculations must be deterministic. Do not ask an LLM to calculate numbers.

Required formulas:
- Loan amount = purchase price - down payment
- Monthly mortgage payment = standard amortized loan payment
- Gross annual rent = monthly rent * 12
- Operating expenses = taxes + insurance + HOA + maintenance + vacancy + management
- NOI = gross annual rent - operating expenses, excluding mortgage
- Annual cash flow = NOI - annual debt service
- Cap rate = NOI / purchase price
- Cash-on-cash return = annual cash flow / initial cash invested
- Break-even rent = monthly rent needed for annual cash flow to equal zero
- DSCR = NOI / annual debt service
- Future sale value = purchase price * (1 + appreciation rate) ^ years
- IRR = annual cash flows plus final sale proceeds minus loan payoff

Recommendation Logic:
Use clear rule-based logic:
- “Buy” if cash flow is positive, DSCR >= 1.20, IRR is attractive, and policy risk is low or moderate.
- “Investigate Further” if returns are close but there are missing data, policy uncertainty, low DSCR, or sensitivity concerns.
- “Reject” if cash flow is strongly negative, DSCR < 1.0, break-even rent is unrealistic, or major policy restrictions exist.

Market and Policy Data:
Create sample JSON data for a few ZIP codes and states. Include:
- Median rent estimate
- Market rent trend
- Property tax notes
- Insurance risk notes
- Landlord-tenant rule summary
- Rent control / rent increase restriction summary
- Short-term rental notes
- HOA/rental restriction warning
- Source label
- Retrieval date
- Confidence level: high, medium, low

If the ZIP code is not found, return a generic state-level fallback and clearly flag:
“Local data not found. This section uses generic state-level or sample data and should be verified.”

Website Requirements:
Make the website feel like a real consulting dashboard, not a landing page.
Include:
- Left or top input section
- Analyze button
- Loading state
- Summary cards for major metrics
- Report sections
- Risk badges
- Opportunity badges
- Final recommendation panel
- Clear missing-data warnings
- Professional styling suitable for a business/finance class demo

Do not overbuild. The MVP should work locally and be easy to demonstrate.

Testing:
Add unit tests for finance.py:
- Mortgage payment calculation
- Cash flow calculation
- Cap rate
- Break-even rent
- IRR
- Recommendation logic

README:
Include setup instructions:
1. Create virtual environment
2. Install requirements
3. Run FastAPI app
4. Open browser at localhost
5. Try a sample property

Deliverable:
A complete local web app that I can run, test, and interact with on my PC. Prioritize reliability and a clean demo over live-data complexity.