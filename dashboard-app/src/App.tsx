import React, { useEffect, useState } from 'react'
import { Tabs } from './components/ui/Tabs'
import { OverviewTab } from './components/overview/OverviewTab'
import { StandupsTab } from './components/standups/StandupsTab'
import { TasksTab } from './components/tasks/TasksTab'
import { AnalyticsTab } from './components/analytics/AnalyticsTab'
import { DependenciesTab } from './components/dependencies/DependenciesTab'
import { ExpertiseTab } from './components/expertise/ExpertiseTab'
import { IncidentsTab } from './components/incidents/IncidentsTab'
import { apiService } from './services/api'
import {
  LayoutDashboardIcon,
  MessageSquareIcon,
  CheckSquareIcon,
  BarChartIcon,
  GitBranchIcon,
  UsersIcon,
  AlertCircleIcon,
} from 'lucide-react'

export function App() {
  const [healthStatus, setHealthStatus] = useState<any>(null)
  const [backendError, setBackendError] = useState(false)
  
  useEffect(() => {
    checkBackendConnection()
  }, [])

  const checkBackendConnection = async () => {
    try {
      const response = await apiService.healthCheck()
      console.log('✅ Backend connected:', response.data)
      setHealthStatus(response.data)
      setBackendError(false)
    } catch (error) {
      console.error('❌ Backend connection failed:', error)
      setBackendError(true)
    }
  }

  const tabs = [
    { id: 'overview', label: 'Overview', icon: <LayoutDashboardIcon className="w-4 h-4" /> },
    { id: 'standups', label: 'Standups', icon: <MessageSquareIcon className="w-4 h-4" /> },
    { id: 'tasks', label: 'Tasks', icon: <CheckSquareIcon className="w-4 h-4" /> },
    { id: 'analytics', label: 'Analytics', icon: <BarChartIcon className="w-4 h-4" /> },
    { id: 'dependencies', label: 'Dependencies', icon: <GitBranchIcon className="w-4 h-4" /> },
    { id: 'expertise', label: 'Expertise', icon: <UsersIcon className="w-4 h-4" /> },
    { id: 'incidents', label: 'Incidents', icon: <AlertCircleIcon className="w-4 h-4" /> },
  ]

  return (
    <div className="min-h-screen w-full bg-gray-50">
      <header className="bg-white border-b border-gray-200 shadow-sm sticky top-0 z-50">
        <div className="px-6 py-4">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-bold bg-gradient-to-r from-indigo-600 to-purple-600 bg-clip-text text-transparent">
                Nexus AI Dashboard
              </h1>
              <p className="text-sm text-gray-600 mt-1">
                AI-powered team intelligence platform
              </p>
            </div>
            {healthStatus ? (
              <div className="flex items-center gap-2 px-3 py-1.5 bg-green-50 border border-green-200 rounded-full">
                <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></div>
                <span className="text-xs font-medium text-green-700">Backend Connected</span>
              </div>
            ) : backendError ? (
              <div className="flex items-center gap-2 px-3 py-1.5 bg-red-50 border border-red-200 rounded-full">
                <div className="w-2 h-2 bg-red-500 rounded-full"></div>
                <span className="text-xs font-medium text-red-700">Backend Offline</span>
              </div>
            ) : (
              <div className="flex items-center gap-2 px-3 py-1.5 bg-gray-100 rounded-full">
                <div className="w-2 h-2 bg-gray-400 rounded-full animate-pulse"></div>
                <span className="text-xs font-medium text-gray-600">Connecting...</span>
              </div>
            )}
          </div>
        </div>
      </header>

      <main className="w-full">
        <Tabs tabs={tabs} defaultTab="overview">
          {(activeTab) => {
            switch (activeTab) {
              case 'overview': return <OverviewTab />
              case 'standups': return <StandupsTab />
              case 'tasks': return <TasksTab />
              case 'analytics': return <AnalyticsTab />
              case 'dependencies': return <DependenciesTab />
              case 'expertise': return <ExpertiseTab />
              case 'incidents':
                return <IncidentsTab />
              default: return <OverviewTab />
            }
          }}
        </Tabs>
      </main>
    </div>
  )
}
