import React from 'react'
import { MailIcon, TrendingUpIcon, UsersIcon, RouteIcon, HeartIcon, FileTextIcon, LayoutDashboardIcon } from 'lucide-react'
export function PlatformFeaturesSection() {
  const features = [
    { icon: <MailIcon size={24} className="text-[#a855f7]" />, title: 'Manager Daily Digest', description: 'Auto-generated summary' },
    { icon: <TrendingUpIcon size={24} className="text-[#a855f7]" />, title: 'Sprint Predictions', description: 'Forecast delays' },
    { icon: <UsersIcon size={24} className="text-[#a855f7]" />, title: 'Expertise Graph', description: 'Know who knows what' },
    { icon: <RouteIcon size={24} className="text-[#a855f7]" />, title: 'AI Help Router', description: 'Smart matching' },
    { icon: <HeartIcon size={24} className="text-[#a855f7]" />, title: 'Team Health', description: 'Mood & workload' },
    { icon: <FileTextIcon size={24} className="text-[#a855f7]" />, title: 'Auto Retros', description: 'AI-generated insights' },
    { icon: <LayoutDashboardIcon size={24} className="text-[#a855f7]" />, title: 'Live Dashboard', description: 'Real-time metrics' },
  ]
  return (
    <section className="py-24 bg-gradient-to-b from-[#1a0b2e] to-[#0f0320]">
      <div className="container mx-auto px-6">
        <h2 className="text-4xl font-bold mb-16 text-center bg-gradient-to-r from-white to-[#f3e8ff] bg-clip-text text-transparent">Platform Features</h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {features.map((f, i) => (
            <div key={i} className="bg-white/5 border border-white/10 rounded-2xl p-6 hover:border-[#a855f7]/40 transition-all">
              <div className="mb-4 p-3 rounded-xl inline-block bg-[#a855f7]/10">{f.icon}</div>
              <h3 className="text-lg font-semibold mb-2">{f.title}</h3>
              <p className="text-[#f3e8ff]/70 text-sm">{f.description}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}