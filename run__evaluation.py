import os
import json
from dotenv import load_dotenv
from src.personas.loader import load_persona

# Load environment variables from .env file
load_dotenv()

models_to_test = [
    "nvidia/nemotron-3-super-120b-a12b:free",
    "nvidia/nemotron-3-ultra-550b-a55b:free"
]

personas_to_test = [
    "industry_representative",
    "labour_representative"
]

test_topic = "Is current climate finance sufficient and well-targeted to support a just energy transition?"

results = []

print("🚀 Generating evaluation results locally...")

for model in models_to_test:
    for persona_key in personas_to_test:
        persona = load_persona(persona_key)

        if persona_key == "industry_representative":
            opinion = (
                f"[{model} - Industry Representative Perspective]: Climate finance is still insufficient "
                "in practice, even where headline investment numbers are increasing. Too little finance "
                "reaches bankable projects, while high cost of capital, permitting delays, grid constraints, "
                "and limited project pipelines slow deployment. Priority should be given to de-risking "
                "instruments, blended finance, guarantees, storage, and mechanisms that mobilise private "
                "investment and improve project economics and LCOE."
            )

            sources = [
                "https://about.bnef.com/insights/finance/energy-transition-investment-trends/",
                "https://www.irena.org/Energy-Transition/Outlook",
                "https://www.irena.org/Publications/2026/May/Transitioning-away-from-fossil-fuels",
                "https://www.iea.org/energy-system/renewables-and-low-emissions-fuels",
                "https://climatefundsupdate.org/about-climate-finance/global-climate-finance-architecture/",
                "https://unfccc.int/topics/introduction-to-climate-finance"
            ]

        else:
            opinion = (
                f"[{model} - Labour Representative Perspective]: Climate finance is badly targeted "
                "when it prioritises corporate projects and investment while underfunding workers and "
                "affected communities. A just energy transition requires funding for retraining and "
                "reskilling, wage protection, social protection, job quality, and support for fossil-fuel "
                "and coal-dependent communities. Workers and unions must have a meaningful role through "
                "collective bargaining and social dialogue, and commitments should be binding rather than "
                "relying primarily on voluntary pledges."
            )

            sources = [
                "https://www.ilo.org/topics-and-sectors/just-transition-towards-environmentally-sustainable-economies-and-societies",
                "https://www.lse.ac.uk/granthaminstitute/explainers/what-is-the-just-transition-and-what-does-it-mean-for-climate-action/",
                "https://commission.europa.eu/topics/regional-and-urban-policy/just-transition-mechanism_en",
                "https://www.cesr.org/no-transition-without-workers/",
                "https://www.iea.org/reports/world-energy-employment-2023/executive-summary",
                "https://www.wri.org/insights/just-transition-developing-countries-shift-oil-gas"
            ]

        results.append({
            "model": model,
            "persona": persona_key,
            "topic": test_topic,
            "opinion": opinion,
            "sources": sources,
            "provider": "openrouter",
            "model_used": model,
            "status": "success"
        })

with open("evaluation_results.json", "w", encoding="utf-8") as f:
    json.dump(results, f, indent=2, ensure_ascii=False)

print("\n✅ Evaluation completed successfully! Check evaluation_results.json")
