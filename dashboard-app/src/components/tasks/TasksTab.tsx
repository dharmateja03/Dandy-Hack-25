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
      // Backend might return { tasks: [...] } or just [...]
      const taskData = response.data.tasks || response.data
      setTasks(Array.isArray(taskData) ? taskData : [])
      console.log('✅ Loaded tasks:', taskData.length)
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
