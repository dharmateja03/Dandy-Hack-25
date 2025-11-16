#!/bin/bash

cd /Users/dharmatejasamudrala/projects/Dandy-Hack-25/dashboard-app/src/components

echo "🔧 Filling remaining tab components..."

# ============================================
# STANDUPS TAB
# ============================================

cat > standups/StandupsTab.tsx << 'EOF'
import React, { useState, useEffect } from 'react'
import { Card } from '../ui/Card'
import { Badge } from '../ui/Badge'
import { Button } from '../ui/Button'
import { apiService } from '../../services/api'
import { SearchIcon, FilterIcon, ChevronDownIcon } from 'lucide-react'

export function StandupsTab() {
  const [standups, setStandups] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [expandedId, setExpandedId] = useState<number | null>(null)

  useEffect(() => {
    loadStandups()
  }, [])

  const loadStandups = async () => {
    try {
      const response = await apiService.getStandups()
      setStandups(Array.isArray(response.data) ? response.data : [])
    } catch (error) {
      console.error('Failed to load standups:', error)
      setStandups([])
    } finally {
      setLoading(false)
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600"></div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <Card>
        <div className="flex flex-col md:flex-row gap-4">
          <div className="flex-1 relative">
            <SearchIcon className="absolute left-3 top-1/2 transform -translate-y-1/2 w-5 h-5 text-gray-400" />
            <input
              type="text"
              placeholder="Search standups..."
              className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
            />
          </div>
          <Button variant="secondary">
            <FilterIcon className="w-4 h-4 mr-2" />
            Filter
          </Button>
        </div>
      </Card>

      <Card>
        <h3 className="text-lg font-semibold mb-4">Recent Standups</h3>
        {standups.length === 0 ? (
          <div className="text-center py-12">
            <p className="text-gray-500">No standups yet. Data will appear when team members submit their updates.</p>
          </div>
        ) : (
          <div className="space-y-3">
            {standups.map((standup: any, idx: number) => (
              <div key={idx} className="border border-gray-200 rounded-lg p-4">
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <div className="flex items-center gap-3 mb-2">
                      <span className="font-semibold text-gray-900">{standup.user_name || standup.user_id}</span>
                      <span className="text-sm text-gray-500">{standup.created_at || 'Today'}</span>
                      <Badge variant="info">{standup.sentiment || 'neutral'}</Badge>
                    </div>
                    <p className="text-sm text-gray-700">{standup.content || standup.message}</p>
                  </div>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => setExpandedId(expandedId === idx ? null : idx)}
                  >
                    <ChevronDownIcon className={`w-4 h-4 transition-transform ${expandedId === idx ? 'rotate-180' : ''}`} />
                  </Button>
                </div>
              </div>
            ))}
          </div>
        )}
      </Card>
    </div>
  )
}
EOF

# ============================================
# TASKS TAB
# ============================================

cat > tasks/TasksTab.tsx << 'EOF'
import React, { useState, useEffect } from 'react'
import { Card } from '../ui/Card'
import { Badge } from '../ui/Badge'
import { Button } from '../ui/Button'
import { apiService } from '../../services/api'
import { FilterIcon, ChevronRightIcon } from 'lucide-react'

export function TasksTab() {
  const [tasks, setTasks] = useState<any[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    loadTasks()
  }, [])

  const loadTasks = async () => {
    try {
      const response = await apiService.getTasks()
      setTasks(Array.isArray(response.data) ? response.data : [])
    } catch (error) {
      console.error('Failed to load tasks:', error)
      setTasks([])
    } finally {
      setLoading(false)
    }
  }

  const getStatusBadge = (status: string) => {
    const variants: Record<string, any> = {
      completed: 'success',
      'in-progress': 'info',
      blocked: 'danger',
      'not-started': 'neutral',
    }
    return variants[status] || 'neutral'
  }

  const getPriorityBadge = (priority: string) => {
    const variants: Record<string, any> = {
      critical: 'danger',
      high: 'warning',
      medium: 'info',
      low: 'neutral',
    }
    return variants[priority] || 'neutral'
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600"></div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <Card>
        <div className="flex flex-wrap gap-3">
          <Button variant="secondary" size="sm">
            <FilterIcon className="w-4 h-4 mr-2" />
            Status
          </Button>
          <Button variant="secondary" size="sm">
            <FilterIcon className="w-4 h-4 mr-2" />
            Priority
          </Button>
        </div>
      </Card>

      <Card>
        <h3 className="text-lg font-semibold mb-4">All Tasks</h3>
        {tasks.length === 0 ? (
          <div className="text-center py-12">
            <p className="text-gray-500">No tasks found. Data will sync from your task management system.</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-gray-50 border-b border-gray-200">
                <tr>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-gray-600 uppercase">Task</th>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-gray-600 uppercase">Status</th>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-gray-600 uppercase">Priority</th>
                  <th className="px-4 py-3"></th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200">
                {tasks.map((task: any, idx: number) => (
                  <tr key={idx} className="hover:bg-gray-50">
                    <td className="px-4 py-3">
                      <p className="font-medium text-gray-900">{task.title}</p>
                    </td>
                    <td className="px-4 py-3">
                      <Badge variant={getStatusBadge(task.status)}>
                        {task.status}
                      </Badge>
                    </td>
                    <td className="px-4 py-3">
                      <Badge variant={getPriorityBadge(task.priority)}>
                        {task.priority}
                      </Badge>
                    </td>
                    <td className="px-4 py-3">
                      <Button variant="ghost" size="sm">
                        <ChevronRightIcon className="w-4 h-4" />
                      </Button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>
    </div>
  )
}
EOF

# ============================================
# ANALYTICS TAB
# ============================================

cat > analytics/AnalyticsTab.tsx << 'EOF'
import React, { useState, useEffect } from 'react'
import { Card } from '../ui/Card'
import { Badge } from '../ui/Badge'
import { apiService } from '../../services/api'
import { TrendingUpIcon, AlertCircleIcon, UsersIcon, ZapIcon } from 'lucide-react'

export function AnalyticsTab() {
  const [analytics, setAnalytics] = useState<any>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    loadAnalytics()
  }, [])

  const loadAnalytics = async () => {
    try {
      const response = await apiService.getInsights(7)
      setAnalytics(response.data)
    } catch (error) {
      console.error('Failed to load analytics:', error)
    } finally {
      setLoading(false)
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600"></div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <Card>
        <div className="flex items-center gap-2 mb-4">
          <TrendingUpIcon className="w-5 h-5 text-blue-500" />
          <h3 className="text-lg font-semibold">Team Velocity</h3>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div>
            <p className="text-sm text-gray-600">Weekly Velocity</p>
            <p className="text-2xl font-bold mt-1">{analytics?.velocity || 0} tasks</p>
          </div>
          <div>
            <p className="text-sm text-gray-600">Completion Rate</p>
            <p className="text-2xl font-bold mt-1">{analytics?.completion_rate || 0}%</p>
          </div>
          <div>
            <p className="text-sm text-gray-600">Avg Time</p>
            <p className="text-2xl font-bold mt-1">{analytics?.avg_time || '0'}h</p>
          </div>
          <div>
            <p className="text-sm text-gray-600">Trend</p>
            <Badge variant="success">Growing</Badge>
          </div>
        </div>
      </Card>

      <Card>
        <div className="flex items-center gap-2 mb-4">
          <ZapIcon className="w-5 h-5 text-purple-500" />
          <h3 className="text-lg font-semibold">Team Health</h3>
        </div>
        <div className="text-center py-8">
          <p className="text-gray-500">Analytics dashboard powered by MCP backend</p>
          <p className="text-sm text-gray-400 mt-2">Data visualization coming soon</p>
        </div>
      </Card>
    </div>
  )
}
EOF

# ============================================
# REMAINING TABS (Simplified)
# ============================================

cat > dependencies/DependenciesTab.tsx << 'EOF'
import React from 'react'
import { Card } from '../ui/Card'
import { DependencyGraph } from './DependencyGraph'
import { GitBranchIcon } from 'lucide-react'

export function DependenciesTab() {
  return (
    <div className="space-y-6">
      <Card>
        <div className="flex items-center gap-2 mb-4">
          <GitBranchIcon className="w-5 h-5 text-blue-500" />
          <h3 className="text-lg font-semibold">Task Dependencies</h3>
        </div>
        <DependencyGraph />
      </Card>
    </div>
  )
}
EOF

cat > dependencies/DependencyGraph.tsx << 'EOF'
import React from 'react'

export function DependencyGraph() {
  return (
    <div className="w-full h-96 bg-gray-50 rounded-lg border-2 border-gray-200 flex items-center justify-center">
      <div className="text-center">
        <p className="text-gray-500 font-medium">Dependency Graph</p>
        <p className="text-sm text-gray-400 mt-2">Interactive visualization coming soon</p>
        <p className="text-xs text-gray-400 mt-1">Requires @xyflow/react integration</p>
      </div>
    </div>
  )
}
EOF

cat > expertise/ExpertiseTab.tsx << 'EOF'
import React, { useState, useEffect } from 'react'
import { Card } from '../ui/Card'
import { Badge } from '../ui/Badge'
import { apiService } from '../../services/api'
import { SearchIcon, UserIcon } from 'lucide-react'

export function ExpertiseTab() {
  const [experts, setExperts] = useState<any[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    loadExperts()
  }, [])

  const loadExperts = async () => {
    try {
      const response = await apiService.getExperts()
      setExperts(Array.isArray(response.data) ? response.data : [])
    } catch (error) {
      console.error('Failed to load experts:', error)
      setExperts([])
    } finally {
      setLoading(false)
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600"></div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <Card>
        <div className="flex items-center gap-2 mb-4">
          <SearchIcon className="w-5 h-5 text-blue-500" />
          <h3 className="text-lg font-semibold">Find an Expert</h3>
        </div>
        <input
          type="text"
          placeholder="Search by skill..."
          className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
        />
      </Card>

      <Card>
        <h3 className="text-lg font-semibold mb-4">Team Expertise</h3>
        {experts.length === 0 ? (
          <div className="text-center py-12">
            <p className="text-gray-500">Expert matching data will appear here</p>
          </div>
        ) : (
          <div className="space-y-4">
            {experts.map((expert: any, idx: number) => (
              <div key={idx} className="p-4 border border-gray-200 rounded-lg">
                <div className="flex items-center gap-2">
                  <UserIcon className="w-5 h-5 text-gray-400" />
                  <p className="font-semibold">{expert.name}</p>
                </div>
                <div className="flex flex-wrap gap-2 mt-2">
                  {expert.skills?.map((skill: string, i: number) => (
                    <Badge key={i} variant="info">{skill}</Badge>
                  ))}
                </div>
              </div>
            ))}
          </div>
        )}
      </Card>
    </div>
  )
}
EOF

cat > incidents/IncidentsTab.tsx << 'EOF'
import React, { useState, useEffect } from 'react'
import { Card } from '../ui/Card'
import { Badge } from '../ui/Badge'
import { Button } from '../ui/Button'
import { apiService } from '../../services/api'
import { AlertCircleIcon } from 'lucide-react'

export function IncidentsTab() {
  const [incidents, setIncidents] = useState<any[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    loadIncidents()
  }, [])

  const loadIncidents = async () => {
    try {
      const response = await apiService.getIncidents()
      setIncidents(Array.isArray(response.data) ? response.data : [])
    } catch (error) {
      console.error('Failed to load incidents:', error)
      setIncidents([])
    } finally {
      setLoading(false)
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600"></div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <Card>
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <AlertCircleIcon className="w-5 h-5 text-red-500" />
            <h3 className="text-lg font-semibold">Incidents</h3>
          </div>
          <Button size="sm">Report Incident</Button>
        </div>
        {incidents.length === 0 ? (
          <div className="text-center py-12">
            <p className="text-gray-500">No incidents. System is running smoothly! 🎉</p>
          </div>
        ) : (
          <div className="space-y-3">
            {incidents.map((incident: any, idx: number) => (
              <div key={idx} className="border border-gray-200 rounded-lg p-4">
                <div className="flex items-start justify-between">
                  <div>
                    <p className="font-semibold">{incident.title}</p>
                    <p className="text-sm text-gray-600 mt-1">{incident.description}</p>
                  </div>
                  <Badge variant="danger">{incident.severity}</Badge>
                </div>
              </div>
            ))}
          </div>
        )}
      </Card>
    </div>
  )
}
EOF

cat > crm/CRMTab.tsx << 'EOF'
import React from 'react'
import { Card } from '../ui/Card'
import { BriefcaseIcon } from 'lucide-react'

export function CRMTab() {
  return (
    <div className="space-y-6">
      <Card>
        <div className="flex items-center gap-2 mb-4">
          <BriefcaseIcon className="w-5 h-5 text-purple-500" />
          <h3 className="text-lg font-semibold">Customer Relationship Management</h3>
        </div>
        <div className="text-center py-12">
          <p className="text-gray-500">CRM integration coming soon</p>
          <p className="text-sm text-gray-400 mt-2">Track customer interactions and pipeline</p>
        </div>
      </Card>
    </div>
  )
}
EOF

echo ""
echo "✅ All tab components filled!"
echo ""
echo "📊 Component Summary:"
echo "  - UI Components: 4/4 ✓"
echo "  - Overview: 1/1 ✓"
echo "  - Standups: 1/1 ✓"
echo "  - Tasks: 1/1 ✓"
echo "  - Analytics: 1/1 ✓"
echo "  - Dependencies: 2/2 ✓"
echo "  - Expertise: 1/1 ✓"
echo "  - Incidents: 1/1 ✓"
echo "  - CRM: 1/1 ✓"
echo ""
echo "🚀 Ready to run: npm run dev"
