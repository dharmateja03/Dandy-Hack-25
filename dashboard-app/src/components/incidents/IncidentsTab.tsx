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
