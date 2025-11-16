import React from 'react'

export function DependencyGraph() {
  return (
    <div className="w-full h-96 bg-gray-50 rounded-lg border-2 border-gray-200 flex items-center justify-center">
      <div className="text-center">
        <p className="text-gray-500 font-medium">Dependency Graph</p>
        <p className="text-sm text-gray-400 mt-2">Interactive visualization coming soon</p>
        <p className="text-xs text-gray-400 mt-1">Requires @xyflow/react integration</p>
      </div>
    </div>
  )
}
