import React, { useState } from 'react'
import { ArrowRightIcon, EyeIcon, EyeOffIcon } from 'lucide-react'

const DUMMY_USERS = [
  { id: 'U001', email: 'john@nexus.ai', password: 'admin123', name: 'John Doe', role: 'Manager' },
  { id: 'U002', email: 'sarah@nexus.ai', password: 'dev123', name: 'Sarah Chen', role: 'Engineer' },
  { id: 'U003', email: 'mike@nexus.ai', password: 'eng123', name: 'Mike Johnson', role: 'Engineer' },
  { id: 'U004', email: 'demo@nexus.ai', password: 'demo', name: 'Demo User', role: 'Manager' },
]

export function LoginPage() {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [error, setError] = useState('')
  const [isLoading, setIsLoading] = useState(false)

  const handleLogin = (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setIsLoading(true)

    setTimeout(() => {
      const user = DUMMY_USERS.find((u) => u.email === email && u.password === password)
      if (user) {
        localStorage.setItem('nexus_user', JSON.stringify(user))
        localStorage.setItem('nexus_auth_token', `token_${user.id}_${Date.now()}`)
        window.location.href = 'http://localhost:3000'
      } else {
        setError('Invalid email or password')
        setIsLoading(false)
      }
    }, 800)
  }

  return (
    <div className="min-h-screen bg-[#0f0320] text-white flex items-center justify-center overflow-hidden">
      <div className="absolute inset-0 z-0">
        <div className="absolute inset-0 bg-gradient-to-br from-[#0f0320] via-[#1a0b2e] to-[#0f0320]"></div>
        <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-[#a855f7]/20 rounded-full blur-3xl"></div>
        <div className="absolute bottom-1/4 right-1/4 w-96 h-96 bg-[#8b5cf6]/20 rounded-full blur-3xl"></div>
      </div>
      <div className="relative z-10 w-full max-w-md px-6">
        <div className="text-center mb-8">
          <h1 className="text-4xl font-bold bg-gradient-to-r from-[#a855f7] to-[#f3e8ff] bg-clip-text text-transparent mb-2">Nexus AI</h1>
          <p className="text-[#f3e8ff]/70">Sign in to your account</p>
        </div>
        <div className="backdrop-blur-xl bg-white/5 border border-white/10 rounded-3xl p-8 shadow-2xl">
          <form onSubmit={handleLogin} className="space-y-6">
            <div>
              <label htmlFor="email" className="block text-sm font-medium text-[#f3e8ff]/90 mb-2">Email Address</label>
              <input id="email" type="email" value={email} onChange={(e) => setEmail(e.target.value)} placeholder="you@example.com" className="w-full px-4 py-3 rounded-xl bg-white/5 border border-white/10 text-white placeholder-[#f3e8ff]/40 focus:outline-none focus:border-[#a855f7] focus:ring-2 focus:ring-[#a855f7]/20 transition-all" required />
            </div>
            <div>
              <label htmlFor="password" className="block text-sm font-medium text-[#f3e8ff]/90 mb-2">Password</label>
              <div className="relative">
                <input id="password" type={showPassword ? 'text' : 'password'} value={password} onChange={(e) => setPassword(e.target.value)} placeholder="Enter your password" className="w-full px-4 py-3 rounded-xl bg-white/5 border border-white/10 text-white placeholder-[#f3e8ff]/40 focus:outline-none focus:border-[#a855f7] focus:ring-2 focus:ring-[#a855f7]/20 transition-all pr-12" required />
                <button type="button" onClick={() => setShowPassword(!showPassword)} className="absolute right-3 top-1/2 -translate-y-1/2 text-[#f3e8ff]/50 hover:text-[#a855f7] transition-colors">
                  {showPassword ? <EyeOffIcon size={20} /> : <EyeIcon size={20} />}
                </button>
              </div>
            </div>
            {error && <div className="bg-red-500/10 border border-red-500/30 rounded-xl p-3 text-red-300 text-sm">{error}</div>}
            <div className="bg-[#a855f7]/10 border border-[#a855f7]/30 rounded-xl p-4">
              <p className="text-xs text-[#f3e8ff]/70 mb-2 font-semibold">Demo Credentials:</p>
              <div className="space-y-1 text-xs text-[#f3e8ff]/60">
                <p>• <span className="text-[#a855f7]">demo@nexus.ai</span> / demo</p>
                <p>• <span className="text-[#a855f7]">john@nexus.ai</span> / admin123</p>
                <p>• <span className="text-[#a855f7]">sarah@nexus.ai</span> / dev123</p>
              </div>
            </div>
            <button type="submit" disabled={isLoading} className="w-full px-6 py-3 rounded-xl bg-gradient-to-r from-[#a855f7] to-[#8b5cf6] text-white font-semibold shadow-lg shadow-[#a855f7]/30 hover:shadow-[#a855f7]/50 transition-all flex items-center justify-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed">
              {isLoading ? (<><div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin"></div>Signing in...</>) : (<>Sign In <ArrowRightIcon size={18} /></>)}
            </button>
          </form>
          <div className="mt-6 text-center">
            <a href="/" className="text-sm text-[#f3e8ff]/70 hover:text-[#a855f7] transition-colors">← Back to Home</a>
          </div>
        </div>
      </div>
    </div>
  )
}