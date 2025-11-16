import React, { useEffect, useState } from 'react'
export function Header() {
  const [isScrolled, setIsScrolled] = useState(false)
  useEffect(() => {
    const handleScroll = () => {
      setIsScrolled(window.scrollY > 10)
    }
    window.addEventListener('scroll', handleScroll)
    return () => window.removeEventListener('scroll', handleScroll)
  }, [])
  return (
    <header className={`fixed top-4 left-4 right-4 z-50 transition-all duration-500 ${isScrolled ? 'top-2 left-8 right-8' : ''}`}>
      <div className={`mx-auto transition-all duration-500 ${isScrolled ? 'max-w-5xl' : 'max-w-7xl'}`}>
        <div className={`rounded-full border border-white/10 backdrop-blur-xl bg-white/5 shadow-lg transition-all duration-500 ${isScrolled ? 'bg-[#1a0b2e]/90 py-2' : 'bg-[#1a0b2e]/60 py-3'}`}>
          <div className="px-6 flex items-center justify-between">
            <span className="text-xl font-semibold bg-gradient-to-r from-[#a855f7] to-[#f3e8ff] bg-clip-text text-transparent">Nexus AI</span>
            <nav className="hidden md:flex items-center space-x-8">
              <a href="#features" className="text-[#f3e8ff]/90 hover:text-white transition-colors text-sm">Features</a>
              <a href="#how-it-works" className="text-[#f3e8ff]/90 hover:text-white transition-colors text-sm">How It Works</a>
              <a href="#pricing" className="text-[#f3e8ff]/90 hover:text-white transition-colors text-sm">Pricing</a>
              <a href="#faq" className="text-[#f3e8ff]/90 hover:text-white transition-colors text-sm">FAQ</a>
            </nav>
            <div className="flex items-center space-x-3">
              <a href="/login" className="px-4 py-2 rounded-full text-[#f3e8ff] hover:text-white transition-colors text-sm">Login</a>
              <a href="/login" className="px-5 py-2 rounded-full bg-gradient-to-r from-[#a855f7] to-[#8b5cf6] text-white hover:shadow-lg hover:shadow-[#a855f7]/50 transition-all text-sm">Get Started</a>
            </div>
          </div>
        </div>
      </div>
    </header>
  )
}