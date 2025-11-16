import React from 'react'
export function LogoSection() {
  const integrations = [
    {
      name: 'GitHub',
      icon: 'https://cdn.simpleicons.org/github/white',
    },
    {
      name: 'Slack',
      icon: 'https://cdn.simpleicons.org/slack/white',
    },
    {
      name: 'Jira',
      icon: 'https://cdn.simpleicons.org/jira/white',
    },
    {
      name: 'Google Docs',
      icon: 'https://cdn.simpleicons.org/googledocs/white',
    },
    {
      name: 'Google Calendar',
      icon: 'https://cdn.simpleicons.org/googlecalendar/white',
    },
  ]
  return (
    <section className="py-16 bg-[#0f0320]">
      <div className="container mx-auto px-6">
        <p className="text-center text-[#f3e8ff]/60 text-sm uppercase tracking-wider mb-8">
          Gathers context from all your tools
        </p>
        <div className="flex flex-wrap justify-center items-center gap-12 md:gap-16">
          {integrations.map((integration, index) => (
            <div
              key={index}
              className="opacity-70 hover:opacity-100 transition-opacity flex items-center gap-3"
            >
              <img
                src={integration.icon}
                alt={integration.name}
                className="h-8 w-8"
              />
              <span className="text-[#f3e8ff] text-lg">{integration.name}</span>
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}