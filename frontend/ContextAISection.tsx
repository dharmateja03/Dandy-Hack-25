import React from 'react'
export function ContextAISection() {
  return (
    <section id="how-it-works" className="py-24 bg-[#0f0320]">
      <div className="container mx-auto px-6">
        <h2 className="text-4xl font-bold mb-8 text-center text-white">How It Works</h2>
        <p className="text-center text-[#f3e8ff]/70 max-w-2xl mx-auto mb-16">Five-step visual flow showing complete automation</p>
        <div className="max-w-4xl mx-auto bg-gradient-to-br from-[#1a0b2e] to-[#0f0320] border border-white/10 rounded-3xl p-12 text-center">
          <div className="text-6xl mb-6">🔄</div>
          <p className="text-xl text-[#f3e8ff]">AI ingests standups → Routes help requests → Updates dashboard in real-time</p>
        </div>
      </div>
    </section>
  )
}
