import React from 'react'
import { Header } from './components/Header'
import { HeroSection } from './components/HeroSection'
import { LogoSection } from './components/LogoSection'
import { MetricsSection } from './components/MetricsSection'
import { FeaturesSection } from './components/FeaturesSection'
import { ContextAISection } from './components/ContextAISection'
import { PlatformFeaturesSection } from './components/PlatformFeaturesSection'
import { LiveMetricsSection } from './components/LiveMetricsSection'
import { CTASection } from './components/CTASection'
import { Footer } from './components/Footer'
export function App() {
  return (
    <div className="min-h-screen bg-[#0f0320] text-white overflow-hidden">
      <Header />
      <HeroSection />
      <LogoSection />
      <MetricsSection />
      <FeaturesSection />
      <ContextAISection />
      <PlatformFeaturesSection />
      <LiveMetricsSection />
      <CTASection />
      <Footer />
    </div>
  )
}
