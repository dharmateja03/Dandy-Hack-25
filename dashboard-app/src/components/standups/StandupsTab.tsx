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
      // Backend returns { standups: [...] }
      const standupData = response.data.standups || response.data
      
      // Map standups to ensure we have user names, not just slack IDs
      const mappedStandups = standupData.map((s: any) => ({
        ...s,
        // Use user_name if available, otherwise fall back to user_id (but not slack_user_id)
        display_name: s.user_name || s.user_id || 'Unknown User'
      }))
      
      setStandups(Array.isArray(mappedStandups) ? mappedStandups : [])
      console.log('✅ Loaded standups:', mappedStandups.length)
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
                      <span className="font-semibold text-gray-900">{standup.display_name}</span>
                      <span className="text-sm text-gray-500">
                        {standup.submitted_at ? new Date(standup.submitted_at).toLocaleDateString() : 'Today'}
                      </span>
                      <Badge variant="info">{standup.sentiment || 'neutral'}</Badge>
                    </div>
                    <p className="text-sm text-gray-700 mb-2">{standup.message || standup.content}</p>
                    {standup.parsed_data && (
                      <div className="text-xs text-gray-500 mt-2 space-y-1">
                        {standup.parsed_data.yesterday && (
                          <div>✅ Yesterday: {String(standup.parsed_data.yesterday)}</div>
                        )}
                        {standup.parsed_data.today && (
                          <div>📋 Today: {String(standup.parsed_data.today)}</div>
                        )}
                        {standup.parsed_data.blockers && (
                          <div>🚧 Blockers: {
                            typeof standup.parsed_data.blockers === 'object' 
                              ? JSON.stringify(standup.parsed_data.blockers)
                              : String(standup.parsed_data.blockers)
                          }</div>
                        )}
                      </div>
                    )}
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
