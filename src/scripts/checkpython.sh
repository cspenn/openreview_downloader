#!/bin/bash
# start checkpython.sh

echo "Running Quality Gate..."

echo "🟢 Running Ruff (Linting & Formatting)..."
ruff check . || exit 1
ruff format --check . || exit 1

echo "🟢 Running Radon (Complexity)..."
# Check if any function has a complexity score of C or worse (C, D, E, F)
BAD_CC=$(radon cc -s src/openreview_downloader | grep -E " [CDEF] \(")
if [ -n "$BAD_CC" ]; then
    echo "🛑 High complexity detected (Target: A or B):"
    echo "$BAD_CC"
    exit 1
fi
echo "Radon CC: All functions are A or B."

echo "🟢 Running Grimp (Architectural Checks)..."
python3 src/scripts/check_cycles.py || exit 1

echo "🟢 Running Pylint..."
export PYTHONPATH=$PYTHONPATH:$(pwd)/src
pylint src/openreview_downloader || exit 1

echo "🟢 Running Semgrep..."
semgrep scan --config auto . || exit 1

echo "🟢 Running Mypy..."
mypy src/openreview_downloader || exit 1

echo "🟢 Running Radon (MI)..."
radon mi src/openreview_downloader || exit 1

echo "🟢 Running Bandit..."
bandit -r src/openreview_downloader || exit 1

echo "🟢 Running Interrogate..."
interrogate src/openreview_downloader || exit 1

echo "🟢 Running Deptry..."
# DEP002: obsolete (alembic, httpx), DEP003: transitive (openreview_downloader), DEP004: dev dependency in code (grimp)
deptry . --pep621-dev-dependency-groups dev --ignore DEP002,DEP003,DEP004 || exit 1

echo "🟢 Running Pytest..."
pytest || exit 1

echo "🟢 Running Pip-audit..."
# Ignore known low-risk 'py' vulnerability from interrogate dependency
pip-audit --ignore-vuln PYSEC-2022-42969 || exit 1

echo "✅ Quality Gate Passed!"

# end checkpython.sh
