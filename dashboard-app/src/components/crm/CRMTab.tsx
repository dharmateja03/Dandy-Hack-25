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
