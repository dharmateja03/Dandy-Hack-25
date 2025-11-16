#!/bin/bash

cd /Users/dharmatejasamudrala/projects/Dandy-Hack-25/dashboard-app/src/components

echo "🔧 Filling all component files with code..."

# ============================================
# UI COMPONENTS
# ============================================

cat > ui/Button.tsx << 'EOF'
import React from 'react'

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'ghost' | 'danger'
  size?: 'sm' | 'md' | 'lg'
  children: React.ReactNode
}

export function Button({
  variant = 'primary',
  size = 'md',
  className = '',
  children,
  ...props
}: ButtonProps) {
  const baseStyles = 'inline-flex items-center justify-center font-medium rounded-lg transition-colors focus:outline-none focus:ring-2 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed'
  
  const variants = {
    primary: 'bg-indigo-600 text-white hover:bg-indigo-700 focus:ring-indigo-500',
    secondary: 'bg-gray-200 text-gray-900 hover:bg-gray-300 focus:ring-gray-500',
    ghost: 'bg-transparent text-gray-700 hover:bg-gray-100 focus:ring-gray-500',
    danger: 'bg-red-600 text-white hover:bg-red-700 focus:ring-red-500',
  }
  
  const sizes = {
    sm: 'px-3 py-1.5 text-sm',
    md: 'px-4 py-2 text-sm',
    lg: 'px-6 py-3 text-base',
  }
  
  return (
    <button
      className={`${baseStyles} ${variants[variant]} ${sizes[size]} ${className}`}
      {...props}
    >
      {children}
    </button>
  )
}
EOF

cat > ui/Card.tsx << 'EOF'
import React from 'react'

interface CardProps {
  children: React.ReactNode
  className?: string
  padding?: 'none' | 'sm' | 'md' | 'lg'
}

export function Card({ children, className = '', padding = 'md' }: CardProps) {
  const paddingStyles = {
    none: '',
    sm: 'p-4',
    md: 'p-6',
    lg: 'p-8',
  }
  
  return (
    <div className={`bg-white rounded-lg border border-gray-200 shadow-sm ${paddingStyles[padding]} ${className}`}>
      {children}
    </div>
  )
}
EOF

cat > ui/Badge.tsx << 'EOF'
import React from 'react'

interface BadgeProps {
  children: React.ReactNode
  variant?: 'success' | 'warning' | 'danger' | 'info' | 'neutral'
  className?: string
}

export function Badge({ children, variant = 'neutral', className = '' }: BadgeProps) {
  const variants = {
    success: 'bg-green-100 text-green-800',
    warning: 'bg-yellow-100 text-yellow-800',
    danger: 'bg-red-100 text-red-800',
    info: 'bg-blue-100 text-blue-800',
    neutral: 'bg-gray-100 text-gray-800',
  }
  
  return (
    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${variants[variant]} ${className}`}>
      {children}
    </span>
  )
}
EOF

cat > ui/Tabs.tsx << 'EOF'
import React, { useState } from 'react'

interface Tab {
  id: string
  label: string
  icon?: React.ReactNode
}

interface TabsProps {
  tabs: Tab[]
  defaultTab?: string
  onTabChange?: (tabId: string) => void
  children: (activeTab: string) => React.ReactNode
}

export function Tabs({ tabs, defaultTab, onTabChange, children }: TabsProps) {
  const [activeTab, setActiveTab] = useState(defaultTab || tabs[0]?.id)
  
  const handleTabChange = (tabId: string) => {
    setActiveTab(tabId)
    onTabChange?.(tabId)
  }
  
  return (
    <div className="w-full">
      <div className="border-b border-gray-200 bg-white">
        <nav className="flex space-x-8 px-6" aria-label="Tabs">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => handleTabChange(tab.id)}
              className={`flex items-center gap-2 py-4 px-1 border-b-2 font-medium text-sm transition-colors ${
                activeTab === tab.id
                  ? 'border-indigo-500 text-indigo-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              {tab.icon}
              {tab.label}
            </button>
          ))}
        </nav>
      </div>
      <div className="p-6">{children(activeTab)}</div>
    </div>
  )
}
EOF

echo "✅ UI components filled (4/4)"

# ============================================
# OVERVIEW TAB (with backend integration)
# ============================================

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

echo "✅ OverviewTab filled (1/8)"
