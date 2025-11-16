import React from 'react'
export function ContextAISection() {
  const steps = [
    { number: '01', title: 'Engineers submit standups', description: 'MCP ingests and processes using AI', angle: -90 },
    { number: '02', title: 'AI identifies blockers & help needs', description: 'Matching engine finds the right expert', angle: -18 },
    { number: '03', title: 'Agentic routing happens automatically', description: 'Help requests delivered directly to the right person', angle: 54 },
    { number: '04', title: 'Managers get auto-escalated insights', description: 'No chasing. No sync delays', angle: 126 },
    { number: '05', title: 'Dashboard updates in real-time', description: 'Progress, velocity, risks, and priorities — continuously refreshed', angle: 198 },
  ]
  
  const getPosition = (angle: number, radius: number = 220) => {
    const radian = (angle * Math.PI) / 180
    return {
      x: Math.cos(radian) * radius,
      y: Math.sin(radian) * radius
    }
  }
  return (
    <section id="how-it-works" className="py-24 bg-[#0f0320] relative overflow-hidden">
      <div className="container mx-auto px-6">
        <div className="text-center mb-16">
          <h2 className="text-3xl md:text-4xl font-bold mb-4 text-white">How It Works</h2>
          <p className="text-[#f3e8ff]/70 max-w-2xl mx-auto text-lg">Five-step visual flow showing the complete automation process</p>
        </div>
        <div className="max-w-6xl mx-auto">
          <div className="relative h-[600px] rounded-3xl bg-gradient-to-br from-[#1a0b2e] to-[#0f0320] border border-white/10 overflow-hidden">
            <div className="absolute inset-0 opacity-20">
              <svg className="w-full h-full" xmlns="http://www.w3.org/2000/svg">
                <defs><pattern id="hexagons" x="50" y="0" width="100" height="100" patternUnits="userSpaceOnUse"><polygon points="50,5 85,25 85,65 50,85 15,65 15,25" fill="none" stroke="rgba(168, 85, 247, 0.3)" strokeWidth="1" /></pattern></defs>
                <rect width="100%" height="100%" fill="url(#hexagons)" />
              </svg>
            </div>
            <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 z-20">
              <div className="relative"><div className="absolute inset-0 bg-[#a855f7] blur-3xl opacity-50"></div>
                <div className="relative w-32 h-32 rounded-2xl bg-gradient-to-br from-[#a855f7] to-[#8b5cf6] flex items-center justify-center shadow-2xl shadow-[#a855f7]/50">
                  <svg className="w-16 h-16 text-white" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M12 2L2 7l10 5 10-5-10-5z" /><path d="M2 17l10 5 10-5" /><path d="M2 12l10 5 10-5" /></svg>
                </div></div>
            </div>
            <svg className="absolute inset-0 z-10" width="100%" height="100%">
              <defs>
                {steps.map((_, index) => (
                  <marker key={`marker-${index}`} id={`arrowhead-${index}`} markerWidth="10" markerHeight="10" refX="9" refY="3" orient="auto">
                    <polygon points="0 0, 10 3, 0 6" fill="#a855f7" opacity="0.6" />
                  </marker>
                ))}
              </defs>
              {steps.map((step, index) => {
                const nextIndex = (index + 1) % steps.length
                const start = getPosition(step.angle)
                const end = getPosition(steps[nextIndex].angle)
                return (
                  <path
                    key={`arrow-${index}`}
                    d={`M ${start.x + 300} ${start.y + 300} Q ${(start.x + end.x) / 2 + 300} ${(start.y + end.y) / 2 + 300} ${end.x + 300} ${end.y + 300}`}
                    stroke="#a855f7"
                    strokeWidth="2"
                    fill="none"
                    opacity="0.4"
                    markerEnd={`url(#arrowhead-${index})`}
                  />
                )
              })}
            </svg>
            {steps.map((step, index) => {
              const pos = getPosition(step.angle)
              return (
                <div
                  key={index}
                  className="absolute z-20"
                  style={{
                    left: '50%',
                    top: '50%',
                    transform: `translate(calc(-50% + ${pos.x}px), calc(-50% + ${pos.y}px))`
                  }}
                >
                  <div className="relative group w-48">
                    <div className="absolute inset-0 bg-[#a855f7]/20 blur-xl group-hover:bg-[#a855f7]/40 transition-all"></div>
                    <div className="relative bg-[#1a0b2e] border border-white/20 rounded-xl p-4 backdrop-blur-sm group-hover:border-[#a855f7]/50 transition-all">
                      <div className="text-[#a855f7] font-bold text-sm mb-2">{step.number}</div>
                      <h3 className="text-white font-semibold text-sm mb-1">{step.title}</h3>
                      <p className="text-[#f3e8ff]/60 text-xs">{step.description}</p>
                    </div>
                  </div>
                </div>
              )
            })}
          </div>
        </div>
      </div>
    </section>
  )
}