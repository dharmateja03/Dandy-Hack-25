import React from 'react'
import { ActivityIcon, AlertTriangleIcon, HelpCircleIcon, ClockIcon, SmileIcon, AlertCircleIcon } from 'lucide-react'
export function LiveMetricsSection() {
  const metrics = [
    { icon: <ActivityIcon size={24} className="text-[#a855f7]" />, label: 'Sprint velocity', value: '87%', trend: 'up' },
    { icon: <AlertTriangleIcon size={24} className="text-[#a855f7]" />, label: 'Active blockers', value: '3' },
    { icon: <HelpCircleIcon size={24} className="text-[#a855f7]" />, label: 'Help requests', value: '5' },
    { icon: <ClockIcon size={24} className="text-[#a855f7]" />, label: 'Response time', value: '12 min' },
    { icon: <SmileIcon size={24} className="text-[#a855f7]" />, label: 'Team mood', value: '8.2/10' },
    { icon: <AlertCircleIcon size={24} className="text-[#a855f7]" />, label: 'Risk alerts', value: '1' },
  ]
  return (
    <section className="py-24 bg-[#0f0320]">
      <div className="container mx-auto px-6">
        <h2 className="text-4xl font-bold mb-16 text-center text-white">Live Team Metrics</h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 max-w-5xl mx-auto">
          {metrics.map((m, i) => (
            <div key={i} className="bg-white/5 border border-white/10 rounded-2xl p-6">
              <div className="flex items-start justify-between mb-4">
                <div className="p-3 rounded-xl bg-[#a855f7]/10">{m.icon}</div>
                {m.trend === 'up' && <span className="text-green-400">↑</span>}
              </div>
              <div className="text-3xl font-bold mb-2">{m.value}</div>
              <div className="text-[#f3e8ff]/70 text-sm">{m.label}</div>
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}