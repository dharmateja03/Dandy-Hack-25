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
