import React from 'react'
import { ArrowRightIcon } from 'lucide-react'
export function CTASection() {
  return (
    <section className="py-24 bg-gradient-to-b from-[#0f0320] to-[#1a0b2e] relative overflow-hidden">
      <div className="absolute inset-0"><div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-96 h-96 bg-[#a855f7]/20 rounded-full blur-3xl"></div></div>
      <div className="container mx-auto px-6 relative z-10">
        <div className="max-w-4xl mx-auto text-center">
          <h2 className="text-5xl font-bold mb-6 bg-gradient-to-r from-white to-[#f3e8ff] bg-clip-text text-transparent">Bring AI-MCP automation to your team</h2>
          <p className="text-xl text-[#f3e8ff]/80 mb-10">Start saving 3+ hours per day</p>
          <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
            <a href="/login" className="px-8 py-4 rounded-full bg-gradient-to-r from-[#a855f7] to-[#8b5cf6] text-white font-semibold shadow-lg hover:shadow-[#a855f7]/50 transition-all flex items-center gap-2">
              Submit Standup <ArrowRightIcon size={18} />
            </a>
            <a href="http://localhost:3000" target="_blank" rel="noopener noreferrer" className="px-8 py-4 rounded-full border border-[#a855f7]/30 bg-white/5 hover:bg-white/10 transition-all font-semibold flex items-center gap-2">
              Explore Dashboard <ArrowRightIcon size={18} />
            </a>
          </div>
        </div>
      </div>
    </section>
  )
}
