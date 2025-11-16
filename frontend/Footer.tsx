import React from 'react'
export function Footer() {
  const currentYear = new Date().getFullYear()
  return (
    <footer className="py-16 bg-[#0f0320] relative overflow-hidden">
      <div className="absolute inset-0 bg-gradient-to-t from-[#1a0b2e] to-[#0f0320]"></div>
      <div className="container mx-auto px-6 relative z-10">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-10">
          <div>
            <div className="text-2xl font-bold bg-gradient-to-r from-[#a855f7] to-[#f3e8ff] bg-clip-text text-transparent mb-4">Nexus AI</div>
            <p className="text-[#f3e8ff]/60 mb-6">AI-powered team intelligence platform built on MCP</p>
          </div>
          <div>
            <h3 className="text-lg font-semibold mb-4">Product</h3>
            <ul className="space-y-3">
              {['Features', 'Platform', 'Integrations'].map(item => (
                <li key={item}><a href="#" className="text-[#f3e8ff]/60 hover:text-[#a855f7] transition-colors">{item}</a></li>
              ))}
            </ul>
          </div>
          <div>
            <h3 className="text-lg font-semibold mb-4">Company</h3>
            <ul className="space-y-3">
              {['About', 'Careers', 'Blog'].map(item => (
                <li key={item}><a href="#" className="text-[#f3e8ff]/60 hover:text-[#a855f7] transition-colors">{item}</a></li>
              ))}
            </ul>
          </div>
          <div>
            <h3 className="text-lg font-semibold mb-4">Resources</h3>
            <ul className="space-y-3">
              {['Docs', 'API', 'Community'].map(item => (
                <li key={item}><a href="#" className="text-[#f3e8ff]/60 hover:text-[#a855f7] transition-colors">{item}</a></li>
              ))}
            </ul>
          </div>
        </div>
        <div className="border-t border-white/10 mt-12 pt-8 text-center">
          <p className="text-[#f3e8ff]/50 text-sm">&copy; {currentYear} Nexus AI. All rights reserved.</p>
        </div>
      </div>
    </footer>
  )
}
