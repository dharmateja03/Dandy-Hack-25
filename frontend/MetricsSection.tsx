import React from 'react'
export function MetricsSection() {
  const metrics = [
    { value: '3+ hours', label: 'saved per engineer/day' },
    { value: '40%', label: 'fewer Slack messages' },
    { value: '0', label: 'recurring meetings required' },
    { value: '2x faster', label: 'blocker resolution' },
    { value: 'Real-time', label: 'visibility' },
  ]
  return (
    <section className="py-16 bg-gradient-to-b from-[#0f0320] to-[#1a0b2e]">
      <div className="container mx-auto px-6">
        <div className="grid grid-cols-1 md:grid-cols-5 gap-8">
          {metrics.map((metric, index) => (
            <div key={index} className="text-center backdrop-blur-md bg-white/5 border border-white/10 rounded-2xl p-6">
              <div className="text-3xl font-bold bg-gradient-to-r from-[#a855f7] to-[#f3e8ff] bg-clip-text text-transparent mb-2">{metric.value}</div>
              <div className="text-[#f3e8ff]/70 text-sm">{metric.label}</div>
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}
