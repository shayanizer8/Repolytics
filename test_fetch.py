import asyncio
from core.analyzer import full_analysis, full_comparison


async def main():
    print("=== SINGLE REPO ANALYSIS ===")
    result = await full_analysis("https://github.com/tiangolo/fastapi")
    
    print("Health Score:", result["health_score"])
    print("Primary Language:", result["tech_stack"]["language"])
    print("Has Tests:", result["tech_stack"]["has_tests"])
    print("Has CI:", result["tech_stack"]["has_ci"])
    print("Days Since Commit:", result["activity"]["days_since_commit"])
    print("README Summary:", result["readme_summary"]["summary"])
    print("Risk Level:", result["code_smells"]["risk_level"])
    print("Flags:", result["code_smells"]["flags"])

    print("\n=== COMPARISON ===")
    comparison = await full_comparison(
        "https://github.com/tiangolo/fastapi",
        "https://github.com/pallets/flask"
    )
    print("Winner:", comparison["comparison"]["winner"])
    print("Verdict:", comparison["comparison"]["verdict"])


asyncio.run(main())
