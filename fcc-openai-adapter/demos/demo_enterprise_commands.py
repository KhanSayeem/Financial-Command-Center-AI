"""
Demo enterprise commands for FCC-AI targeting PE firms and SaaS CFOs.
These are high-value prompts that demonstrate the system's capabilities.
"""

demo_commands = [
    {
        "name": "Portfolio Company Financial Health Assessment",
        "description": "Comprehensive financial analysis for PE firms evaluating portfolio companies",
        "prompt": """As a partner at a private equity firm, I need to assess the financial health of our portfolio company "TechFlow Solutions" before the quarterly board meeting. 
Please provide:
1. Current financial health score and key metrics
2. Revenue trends over the last 12 months
3. Cash flow analysis and liquidity position
4. Key financial ratios compared to industry benchmarks
5. Red flags or areas of concern that need immediate attention
6. Recommendations for improvement in the next 90 days

Use data from Xero and Plaid integrations to provide accurate insights."""
    },
    {
        "name": "SaaS Revenue Forecasting and ARR Analysis",
        "description": "Revenue forecasting and analysis for SaaS CFOs",
        "prompt": """I'm the CFO of a SaaS company with 2,500 customers. I need to prepare our Q3 board presentation focusing on:
1. Current ARR (Annual Recurring Revenue) and growth rate
2. Revenue forecast for the next 12 months with best/worst case scenarios
3. Churn rate analysis and customer lifetime value
4. Expansion revenue from existing customers
5. Cash flow projections for hiring plans in Q4
6. Key metrics to include in our investor update

Please use our Xero data and Stripe payment information to generate these insights."""
    },
    {
        "name": "Due Diligence Financial Analysis",
        "description": "Pre-acquisition due diligence for PE firms",
        "prompt": """We're considering acquiring "DataCore Analytics" for $15M. As part of our due diligence, I need a comprehensive financial analysis:
1. Historical revenue and profit trends (3 years)
2. Recurring vs. non-recurring revenue breakdown
3. Customer concentration risk analysis
4. Key expense categories and cost structure
5. Working capital requirements and cash flow patterns
6. Debt obligations and contingent liabilities
7. Quality of financial reporting and controls

Please analyze their Xero financials and identify any red flags or opportunities."""
    },
    {
        "name": "Monthly Financial Dashboard Review",
        "description": "Automated monthly financial review for SaaS CFOs",
        "prompt": """It's the first of the month and I need my automated financial dashboard review:
1. Key performance indicators (KPIs) vs. budget
2. Cash position and burn rate analysis
3. Revenue recognition summary
4. Accounts receivable aging and collection effectiveness
5. Accounts payable status and vendor relationships
6. Payroll and equity compensation expense tracking
7. Upcoming financial obligations and cash requirements

Highlight any metrics that are outside of normal ranges and require immediate attention."""
    },
    {
        "name": "Fundraising Financial Package Preparation",
        "description": "Financial package preparation for growth-stage companies raising capital",
        "prompt": """We're preparing for our Series B fundraising round and need to create a compelling financial package for potential investors:
1. Financial highlights and growth metrics (last 24 months)
2. Unit economics analysis (CAC, LTV, payback period)
3. Gross margin and operating margin trends
4. Capital efficiency and runway analysis
5. Key assumptions for our 3-year financial model
6. Comparison to public company comparables in our sector
7. Use of funds and expected milestones

Please compile this information from our Xero, Stripe, and Plaid data, ensuring all metrics are investor-ready."""
    }
]

# Function to get a specific demo command by name
def get_demo_command(name: str) -> dict:
    """Get a specific demo command by name."""
    for command in demo_commands:
        if command["name"] == name:
            return command
    return None

# Function to list all demo commands
def list_demo_commands() -> list:
    """List all available demo commands."""
    return [{"name": cmd["name"], "description": cmd["description"]} for cmd in demo_commands]