import React from 'react'
import { ArrowRightIcon } from 'lucide-react'
export function HeroSection() {
  return (
    <section className="relative min-h-screen flex items-center justify-center overflow-hidden">
      <div className="absolute inset-0 z-0 bg-gradient-to-br from-[#0f0320] via-[#1a0b2e] to-[#0f0320]">
        <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-[#a855f7]/20 rounded-full blur-3xl"></div>
        <div className="absolute bottom-1/4 right-1/4 w-96 h-96 bg-[#8b5cf6]/20 rounded-full blur-3xl"></div>
      </div>
      <div className="container mx-auto px-6 pt-32 pb-20 relative z-10 text-center">
        <div className="max-w-4xl mx-auto">
          <h1 className="text-5xl md:text-7xl font-medium leading-tight mb-6">
            <span className="bg-gradient-to-r from-white via-[#f3e8ff] to-[#a855f7] bg-clip-text text-transparent">
              AI-Powered Team Intelligence Platform Built on MCP
            </span>
          </h1>
          <p className="text-2xl text-white mb-4">Eliminate coordination chaos. Save 3+ hours/day through fully-agentic async workflows.</p>
          <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
            <a href="/login" className="px-8 py-3 rounded-full bg-gradient-to-r from-[#a855f7] to-[#8b5cf6] text-white text-lg shadow-lg hover:shadow-[#a855f7]/50 transition-all flex items-center gap-2">
              Start Standup <ArrowRightIcon size={16} />
            </a>
            <a href="http://localhost:3000" target="_blank" rel="noopener noreferrer" className="px-8 py-3 rounded-full border border-[#a855f7]/30 bg-white/5 hover:bg-white/10 transition-all text-lg flex items-center gap-2">
              Open Dashboard <ArrowRightIcon size={16} />
            </a>
          </div>
        </div>
      </div>
    </section>
  )
}