#!/usr/bin/env python3
"""Quick edge case testing to prove real execution."""

import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tests.test_workflow_trace import WorkflowSimulator


async def test_various_queries():
    queries = [
        "gibberish xyz123 random words",
        "ezLog debug my application",
        "search sharepoint for quarterly reports",
        "call another agent and chain the results",
    ]

    for q in queries:
        print(f"\n{'='*60}")
        print(f"QUERY: {q}")
        print("=" * 60)

        with WorkflowSimulator(verbose=False) as sim:
            await sim.run_query(q)
            print(f"Discovered: {sim.discovered_functions}")
            print(f"Code generated: {len(sim.generated_code) if sim.generated_code else 0} chars")
            if sim.validation_result:
                status = "PASS" if sim.validation_result.valid else "FAIL"
                print(f"Validation: {status}")


if __name__ == "__main__":
    asyncio.run(test_various_queries())
