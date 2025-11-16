#!/bin/bash

echo "🚀 Creating Nexus AI Dashboard with Backend Integration..."

cd /Users/dharmatejasamudrala/projects/Dandy-Hack-25

# Create folder structure
mkdir -p dashboard-app/src/{components/{ui,overview,standups,tasks,analytics,dependencies,expertise,incidents,crm},services}

cd dashboard-app

# Create package.json
cat > package.json << 'EOF'
{
  "name": "nexus-dashboard",
  "version": "1.0.0",
  "private": true,
  "type": "module",
  "scripts": {
    "dev": "vite --port 3000",
    "build": "tsc && vite build",
    "preview": "vite preview"
  },
  "dependencies": {
    "@xyflow/react": "^12.3.5",
    "axios": "^1.7.9",
    "lucide-react": "^0.468.0",
    "react": "^18.3.1",
    "react-dom": "^18.3.1"
  },
  "devDependencies": {
    "@types/react": "^18.3.17",
    "@types/react-dom": "^18.3.5",
    "@vitejs/plugin-react": "^4.3.4",
    "autoprefixer": "^10.4.20",
    "postcss": "^8.4.49",
    "tailwindcss": "^3.4.17",
    "typescript": "^5.7.2",
    "vite": "^6.0.5"
  }
}
EOF

# Create .env
cat > .env << 'EOF'
VITE_API_URL=http://localhost:8000
EOF

# Create vite.config.ts
cat > vite.config.ts << 'EOF'
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
})
EOF

# Create tsconfig files
cat > tsconfig.json << 'EOF'
{
  "compilerOptions": {
    "target": "ES2020",
    "useDefineForClassFields": true,
    "lib": ["ES2020", "DOM", "DOM.Iterable"],
    "module": "ESNext",
    "skipLibCheck": true,
    "moduleResolution": "bundler",
    "allowImportingTsExtensions": true,
    "resolveJsonModule": true,
    "isolatedModules": true,
    "noEmit": true,
    "jsx": "react-jsx",
    "strict": true
  },
  "include": ["src"]
}
EOF

cat > tsconfig.node.json << 'EOF'
{
  "compilerOptions": {
    "composite": true,
    "skipLibCheck": true,
    "module": "ESNext",
    "moduleResolution": "bundler",
    "allowSyntheticDefaultImports": true
  },
  "include": ["vite.config.ts"]
}
EOF

# Create tailwind.config.js
cat > tailwind.config.js << 'EOF'
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        primary: '#6366f1',
        secondary: '#8b5cf6',
      },
    },
  },
  plugins: [],
}
EOF

# Create postcss.config.js
cat > postcss.config.js << 'EOF'
export default {
  plugins: {
    tailwindcss: {},
    autoprefixer: {},
  },
}
EOF

# Create index.html
cat > index.html << 'EOF'
<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>Nexus AI - Dashboard</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/index.tsx"></script>
  </body>
</html>
EOF

# Create API service with REAL backend connection
cat > src/services/api.ts << 'EOF'
import axios from 'axios'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

const api = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Add response interceptor for error handling
api.interceptors.response.use(
  response => response,
  error => {
    console.error('API Error:', error.response?.data || error.message)
    return Promise.reject(error)
  }
)

export const apiService = {
  // Health check
  healthCheck: () => api.get('/health'),
  
  // Analytics
  getTodayDigest: () => api.get('/api/digest/today'),
  getInsights: (days: number = 7) => api.get(`/api/insights/trends?days=${days}`),
  getAnalyticsSummary: () => api.get('/api/analytics/summary'),
  
  // Standups
  getStandups: () => api.get('/api/standups/'),
  submitStandup: (data: any) => api.post('/api/standups/', data),
  
  // Tasks
  getTasks: () => api.get('/api/tasks/'),
  getTaskById: (id: string) => api.get(`/api/tasks/${id}`),
  
  // Help Requests
  getHelpRequests: () => api.get('/api/help/'),
  createHelpRequest: (data: any) => api.post('/api/help/', data),
  
  // Blockers
  getBlockers: () => api.get('/api/blockers/'),
  resolveBlocker: (id: string) => api.post(`/api/blockers/${id}/resolve`),
  
  // Users
  getUsers: () => api.get('/api/users/'),
  getUserById: (id: string) => api.get(`/api/users/${id}`),
  
  // Workload
  getWorkload: () => api.get('/api/workload/'),
  
  // Sprint
  getSprintData: () => api.get('/api/sprint/'),
  
  // Incidents
  getIncidents: () => api.get('/api/incidents/'),
  createIncident: (data: any) => api.post('/api/incidents/', data),
  
  // Expertise
  getExperts: (skill?: string) => api.get(`/api/expertise/experts${skill ? `?skill=${skill}` : ''}`),
  getSkills: () => api.get('/api/expertise/skills'),
}

export default api
EOF

echo "✅ Dashboard structure created!"
echo ""
echo "📦 Installing dependencies..."
npm install

echo ""
echo "✅ Setup complete!"
echo ""
echo "🚀 To start the dashboard:"
echo "   cd dashboard-app"
echo "   npm run dev"
echo ""
echo "Dashboard will run on: http://localhost:3000"
echo "Backend API should be on: http://localhost:8000"
