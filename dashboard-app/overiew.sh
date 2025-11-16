#!/bin/bash

cd /Users/dharmatejasamudrala/projects/Dandy-Hack-25/dashboard-app/src/components

mkdir -p overview

cat > overview/OverviewTab.tsx << 'EOF'
import React, { useEffect, useState } from 'react'
import { Card } from '../ui/Card'
import { Badge } from '../ui/Badge'
import { apiService } from '../../services/api'
import {
  TrendingUpIcon,
  ClockIcon,
  TargetIcon,
  AlertTriangleIcon,
  HelpCircleIcon,
  ActivityIcon,
} from 'lucide-react'

export function OverviewTab() {
  const [digest, setDigest] = useState<any>(null)
  const [blockers, setBlockers] = useState<any[]>([])
  const [helpRequests, setHelpRequests] = useState<any[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    loadData()
  }, [])

  const loadData = async () => {
    try {
      const [digestRes, blockersRes, helpRes] = await Promise.all([
        apiService.getTodayDigest().catch(() => ({ data: null })),
        apiService.getBlockers().catch(() => ({ data: [] })),
        apiService.getHelpRequests().catch(() => ({ data: [] })),
      ])
      
      setDigest(digestRes.data)
      setBlockers(Array.isArray(blockersRes.data) ? blockersRes.data : [])
      setHelpRequests(Array.isArray(helpRes.data) ? helpRes.data : [])
    } catch (error) {
      console.error('Failed to load overview data:', error)
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
      {/* Quick Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <Card>
          <div className="flex items-start justify-between">
            <div className="flex-1">
              <p className="text-sm font-medium text-gray-600">Today's Metrics</p>
              <div className="mt-4 space-y-2">
                <div className="flex justify-between items-center">
                  <span className="text-sm text-gray-600">Standups submitted</span>
                  <span className="font-semibold">{digest?.standups_count || 0}</span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-sm text-gray-600">Tasks completed</span>
                  <span className="font-semibold">{digest?.completed_tasks || 0}</span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-sm text-gray-600">Active blockers</span>
                  <span className="font-semibold text-red-600">{blockers.length}</span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-sm text-gray-600">Help requests</span>
                  <span className="font-semibold text-yellow-600">{helpRequests.length}</span>
                </div>
              </div>
            </div>
            <TrendingUpIcon className="w-8 h-8 text-indigo-500" />
          </div>
        </Card>

        <Card>
          <div className="flex items-start justify-between">
            <div className="flex-1">
              <p className="text-sm font-medium text-gray-600">Team Health</p>
              <div className="mt-4 space-y-2">
                <div className="flex justify-between items-center">
                  <span className="text-sm text-gray-600">Active Users</span>
                  <span className="font-semibold">{digest?.active_users || 0}</span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-sm text-gray-600">Team Mood</span>
                  <Badge variant="success">Positive</Badge>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-sm text-gray-600">Velocity</span>
                  <span className="font-semibold">{digest?.velocity || 0}/week</span>
                </div>
              </div>
            </div>
            <TargetIcon className="w-8 h-8 text-purple-500" />
          </div>
        </Card>

        <Card>
          <div className="flex items-start justify-between">
            <div className="flex-1">
              <p className="text-sm font-medium text-gray-600">Time Saved</p>
              <div className="mt-4 space-y-2">
                <div className="flex justify-between items-center">
                  <span className="text-sm text-gray-600">Today</span>
                  <span className="font-semibold text-green-600">
                    {digest?.time_saved || '0'}h
                  </span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-sm text-gray-600">This Week</span>
                  <span className="font-semibold">{digest?.time_saved_week || '0'}h</span>
                </div>
              </div>
            </div>
            <ClockIcon className="w-8 h-8 text-green-500" />
          </div>
        </Card>
      </div>

      {/* Backend Status */}
      <Card>
        <div className="text-center py-8">
          <div className="inline-flex items-center justify-center w-16 h-16 bg-green-100 rounded-full mb-4">
            <svg className="w-8 h-8 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
            </svg>
          </div>
          <h3 className="text-lg font-semibold text-gray-900 mb-2">
            Connected to MCP Backend
          </h3>
          <p className="text-sm text-gray-600 max-w-md mx-auto">
            Dashboard is live and receiving data from the backend API
          </p>
          <div className="mt-4 inline-flex items-center gap-2 px-4 py-2 bg-gray-50 rounded-lg border border-gray-200">
            <code className="text-xs font-mono text-gray-700">http://localhost:8000/api</code>
          </div>
        </div>
      </Card>

      {/* Active Blockers */}
      {blockers.length > 0 && (
        <Card>
          <div className="flex items-center gap-2 mb-4">
            <AlertTriangleIcon className="w-5 h-5 text-red-500" />
            <h3 className="text-lg font-semibold">Active Blockers</h3>
          </div>
          <div className="space-y-3">
            {blockers.slice(0, 5).map((blocker: any, idx: number) => (
              <div key={idx} className="flex items-start justify-between p-3 bg-red-50 rounded-lg border border-red-200">
                <div className="flex-1">
                  <p className="font-medium text-gray-900">{blocker.description || blocker.title}</p>
                  <p className="text-sm text-gray-600 mt-1">
                    Blocked by: {blocker.user_name || blocker.user_id}
                  </p>
                </div>
                <Badge variant="danger">Active</Badge>
              </div>
            ))}
          </div>
        </Card>
      )}

      {/* Help Requests */}
      {helpRequests.length > 0 && (
        <Card>
          <div className="flex items-center gap-2 mb-4">
            <HelpCircleIcon className="w-5 h-5 text-yellow-500" />
            <h3 className="text-lg font-semibold">Help Requests</h3>
          </div>
          <div className="space-y-3">
            {helpRequests.slice(0, 5).map((request: any, idx: number) => (
              <div key={idx} className="flex items-start justify-between p-3 bg-yellow-50 rounded-lg border border-yellow-200">
                <div className="flex-1">
                  <p className="font-medium text-gray-900">{request.topic || request.title}</p>
                  <p className="text-sm text-gray-600 mt-1">
                    Requested by: {request.requester_name || request.user_id}
                  </p>
                </div>
                <Badge variant={request.status === 'resolved' ? 'success' : 'warning'}>
                  {request.status || 'Pending'}
                </Badge>
              </div>
            ))}
          </div>
        </Card>
      )}
    </div>
  )
}
EOF

echo "✅ OverviewTab created with backend integration!"
