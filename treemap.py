# pip install plotly pandas
# (most recent versions of plotly already include express)

import plotly.express as px
import pandas as pd

# ── Sample hierarchical data for AI companies in India (2026 context) ──
data = {
    "Sector": [
        # Level 1
        "Sovereign / Foundational", "Sovereign / Foundational", "Sovereign / Foundational",
        "Enterprise / Conversational", "Enterprise / Conversational", "Enterprise / Conversational",
        "Healthcare / Vertical", "Healthcare / Vertical",
        "Other High-Impact", "Other High-Impact", "Other High-Impact",
        "Major IT Services", "Major IT Services", "Major IT Services",
    ],
    "SubCategory_Company": [
        # Level 2 & 3 (company names)
        "Sarvam AI", "Krutrim", "Neysa",
        "Kore.ai", "Uniphore", "Haptik",
        "Qure.ai", "Niramai",
        "Innovaccer", "HyperVerge", "Observe.AI",
        "TCS", "Infosys", "Wipro",
    ],
    "Value": [  # size of rectangles (fake – replace with real metric: funding in $M, valuation, etc.)
        120, 850, 450,    # Sovereign
        620, 980, 180,    # Enterprise
        140, 90,          # Healthcare
        320, 210, 160,    # Other
        1500, 1200, 900   # IT giants (much larger scale)
    ],
    "Funding_M_USD": [  # just for hover tooltip (optional)
        53, 1000, 300,
        620, 950, 150,
        120, 80,
        300, 190, 140,
        "Very large", "Very large", "Very large"
    ],
    "City": [
        "Bengaluru", "Bengaluru", "Bengaluru",
        "Bengaluru", "Bengaluru", "Bengaluru",
        "Mumbai", "Bengaluru",
        "Noida", "Bengaluru", "Bengaluru",
        "Mumbai", "Bengaluru", "Noida"
    ]
}

df = pd.DataFrame(data)

# ── Create interactive treemap ──
fig = px.treemap(
    df,
    path=[px.Constant("AI India Ecosystem"), "Sector", "SubCategory_Company"],  # hierarchy
    values="Value",                     # size of rectangles
    color="Sector",                     # color by top-level category
    hover_data=["Funding_M_USD", "City"],  # extra info on hover
    color_discrete_sequence=px.colors.qualitative.Bold,  # nicer colors
    title="Interactive Treemap: AI-Dependent Companies in India (2026 snapshot)"
)

# Improve layout & readability
fig.update_traces(
    textinfo="label+value+percent root",   # show label + value + % of total
    textfont_size=14,
    marker_line_width=1.5,
    marker_line_color="darkslategray"
)

fig.update_layout(
    margin=dict(t=50, r=10, b=10, l=10),
    height=750,
    title_font_size=22
)

# Show in browser (interactive!)
fig.show()

# Optional: save as self-contained HTML file you can open anywhere
# fig.write_html("ai_india_treemap_interactive.html")