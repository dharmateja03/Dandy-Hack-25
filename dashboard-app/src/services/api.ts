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
  getStandups: () => api.get('/api/standups/recent'),
  submitStandup: (data: any) => api.post('/api/standups/submit', data),
  
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
