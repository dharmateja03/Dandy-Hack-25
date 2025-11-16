#!/bin/bash

cd /Users/dharmatejasamudrala/projects/Dandy-Hack-25/dashboard-app/src

echo "📁 Creating complete file structure..."

# Create all component directories
mkdir -p components/{ui,overview,standups,tasks,analytics,dependencies,expertise,incidents,crm}

# Create all files (empty initially)
touch components/ui/Button.tsx
touch components/ui/Card.tsx
touch components/ui/Badge.tsx
touch components/ui/Tabs.tsx

touch components/overview/OverviewTab.tsx

touch components/standups/StandupsTab.tsx

touch components/tasks/TasksTab.tsx

touch components/analytics/AnalyticsTab.tsx

touch components/dependencies/DependenciesTab.tsx
touch components/dependencies/DependencyGraph.tsx

touch components/expertise/ExpertiseTab.tsx

touch components/incidents/IncidentsTab.tsx

touch components/crm/CRMTab.tsx

echo "✅ All files created! Total files:"
echo ""
echo "UI Components (4):"
ls -1 components/ui/
echo ""
echo "Tab Components (8):"
ls -1 components/*/
echo ""
echo "🎯 Ready for code to be filled in!"
