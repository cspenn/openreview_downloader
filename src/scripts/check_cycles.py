import grimp
import sys
import os

# Add src directory to path so grimp can find the package
# Assumes script is run from project root: python3 src/scripts/check_cycles.py
sys.path.insert(0, os.path.join(os.getcwd(), "src"))

try:
    print("Building import graph for 'openreview_downloader'...")
    graph = grimp.build_graph("openreview_downloader")

    # nominate_cycle_breakers returns an empty list if there are no cycles
    cycle_breakers = graph.nominate_cycle_breakers(package="openreview_downloader")

    if cycle_breakers:
        print("🛑 Circular dependencies (or cycles) detected!")
        print(f"Number of cycles/cycle breakers: {len(cycle_breakers)}")
        # Grimp doesn't easily list the full cycle paths via this method,
        # but the presence of any means it fails.
        sys.exit(1)
    else:
        print("✅ No circular dependencies found.")
except Exception as e:
    print(f"❌ Error building graph: {e}")
    sys.exit(1)
