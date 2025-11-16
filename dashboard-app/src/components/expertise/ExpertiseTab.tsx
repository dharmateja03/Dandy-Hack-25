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
