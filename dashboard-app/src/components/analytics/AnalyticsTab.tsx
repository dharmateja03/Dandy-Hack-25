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
