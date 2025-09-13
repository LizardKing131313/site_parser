import pathlib
import xml.etree.ElementTree as elementTree

import anybadge


# File paths
badge_file = pathlib.Path("badges/coverage.svg")
badge_file.parent.mkdir(parents=True, exist_ok=True)

# Parse the coverage.xml file to get the line-rate
# If the file does not exist or is invalid, set coverage to 0.
coverage = 0.0
try:
    coverage_xml = pathlib.Path("coverage.xml")
    tree = elementTree.parse(coverage_xml)
    root = tree.getroot()
    coverage = float(root.attrib["line-rate"]) * 100
except Exception as e:
    print(f"Failed to parse coverage.xml {e}")
coverage = round(coverage, 1)

thresholds = {50: "red", 75: "orange", 90: "green"}

badge = anybadge.Badge("Coverage", coverage, thresholds=thresholds)
badge.write_badge(badge_file, overwrite=True)

print(f"Generated badge at badges/coverage.svg (coverage: {coverage:.1f}%)")
