import React from 'react'
import { MessageSquareIcon, ZapIcon, ClockIcon } from 'lucide-react'
export function FeaturesSection() {
  const features = [
    { icon: <MessageSquareIcon size={32} className="text-[#a855f7]" />, title: 'Clutter-Free Communication', description: 'AI reduces 40% of Slack messages.' },
    { icon: <ZapIcon size={32} className="text-[#a855f7]" />, title: 'Autonomous Standups', description: 'No meetings. MCP agents handle everything.' },
    { icon: <ClockIcon size={32} className="text-[#a855f7]" />, title: 'Save 3+ Hours Daily', description: 'Focus on building, not coordination.' },
  ]
  return (
    <section id="features" className="py-24 bg-[#1a0b2e]">
      <div className="container mx-auto px-6">
        <h2 className="text-4xl font-bold mb-16 text-center bg-gradient-to-r from-white to-[#f3e8ff] bg-clip-text text-transparent">Key Features</h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
          {features.map((feature, index) => (
            <div key={index} className="bg-white/5 border border-white/10 rounded-2xl p-8 hover:border-[#a855f7]/40 transition-all">
              <div className="mb-5 p-3 rounded-xl inline-block bg-[#a855f7]/10">{feature.icon}</div>
              <h3 className="text-xl font-semibold mb-3">{feature.title}</h3>
              <p className="text-[#f3e8ff]/70">{feature.description}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}
