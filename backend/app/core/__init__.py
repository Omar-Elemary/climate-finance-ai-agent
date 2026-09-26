"""Shared backend configuration (Persona 3 owned).

Topics are curated from the repo's actual domains (Week 2/3 demos, personas,
climate-finance corpus) — not invented. Personas listed per topic are verified
against personas/*.json filenames.
"""
from __future__ import annotations

# Default agents when POST /discussions omits `personas`.
# All three exist as personas/<name>.json: investor, policy_expert, scientist.
DEFAULT_PERSONAS: list[str] = ["investor", "policy_expert", "scientist"]

# Upper bound keeps a single HTTP request from running away.
MAX_ROUNDS = 10

# Curated discussion topics grounded in this repo:
# - week3_demo.py topic (green hydrogen / industrial decarbonization)
# - week2_demo.py default topic (adaptation finance)
# - Week 1 corpus themes (IPCC/UNFCCC/IRENA/IEA/WRI/ILO) + persona focus areas.
TOPICS: list[dict] = [
    {
        "id": "industrial-decarbonization",
        "title": "Financing Industrial Decarbonization and Green Hydrogen",
        "domain": "mitigation",
        "description": "Week 3 demo topic: bankability, blended finance, guarantees, taxonomy and MRV for green hydrogen.",
        "suggested_personas": ["investor", "policy_expert", "env_specialist", "cfo_agent"],
    },
    {
        "id": "adaptation-finance",
        "title": "Should developed countries significantly increase climate adaptation finance for developing nations?",
        "domain": "adaptation",
        "description": "Week 2 demo default topic: equity/CBDR, adaptation needs, loss and damage.",
        "suggested_personas": ["investor", "policy_expert", "scientist"],
    },
    {
        "id": "fossil-fuel-subsidies",
        "title": "Should fossil fuel subsidies be eliminated?",
        "domain": "policy",
        "description": "Week 2 demo CLI example topic: subsidy reform, just transition, stranded assets.",
        "suggested_personas": ["policy_expert", "labour_representative", "cfo_agent"],
    },
    {
        "id": "green-bonds",
        "title": "Are green bonds delivering additional climate impact or greenwashing?",
        "domain": "finance",
        "description": "Investor/ESG focus: additionality, taxonomy alignment, anti-greenwashing, disclosure.",
        "suggested_personas": ["investor", "env_specialist", "policy_compliance_officer"],
    },
    {
        "id": "just-transition",
        "title": "How should climate finance support a just transition for workers?",
        "domain": "social",
        "description": "ILO/labour focus: jobs, reskilling, social protection in the net-zero transition.",
        "suggested_personas": ["labour_representative", "policy_expert", "industry_representative"],
    },
    {
        "id": "solar-roi",
        "title": "What is the ROI of a $1M utility-scale solar investment?",
        "domain": "finance",
        "description": "Financial-calculator path (Agent keyword router: roi/npv/calculate) with grounded retrieval.",
        "suggested_personas": ["investor", "cfo_agent", "scientist"],
    },
]
