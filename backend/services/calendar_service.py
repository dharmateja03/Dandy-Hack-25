"""
Google Calendar Integration Service
Track meetings and calculate time saved
"""

import logging
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import json
import os

logger = logging.getLogger(__name__)


class GoogleCalendarService:
    """Google Calendar integration for meeting tracking"""

    def __init__(self, credentials_path: str = None, token_path: str = None):
        self.credentials_path = credentials_path
        self.token_path = token_path
        self.service = None

        # Initialize will be called explicitly
        self._initialized = False

    async def initialize(self):
        """Initialize Google Calendar API"""
        try:
            from google.auth.transport.requests import Request
            from google.oauth2.credentials import Credentials
            from google_auth_oauthlib.flow import InstalledAppFlow
            from googleapiclient.discovery import build

            SCOPES = ['https://www.googleapis.com/auth/calendar.readonly']

            creds = None

            # Load token if exists
            if self.token_path and os.path.exists(self.token_path):
                creds = Credentials.from_authorized_user_file(self.token_path, SCOPES)

            # If no valid credentials, authenticate
            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    creds.refresh(Request())
                elif self.credentials_path and os.path.exists(self.credentials_path):
                    flow = InstalledAppFlow.from_client_secrets_file(
                        self.credentials_path, SCOPES)
                    creds = flow.run_local_server(port=0)

                    # Save token for future use
                    if self.token_path:
                        with open(self.token_path, 'w') as token:
                            token.write(creds.to_json())
                else:
                    logger.warning("No Google Calendar credentials found")
                    return False

            self.service = build('calendar', 'v3', credentials=creds)
            self._initialized = True
            logger.info("Google Calendar service initialized")
            return True

        except Exception as e:
            logger.error(f"Failed to initialize Google Calendar: {e}")
            return False

    async def sync_meetings(self, user_email: str, days: int = 30) -> List[Dict]:
        """Fetch meetings for a user"""
        if not self._initialized:
            logger.error("Calendar service not initialized")
            return []

        try:
            # Get events from primary calendar
            now = datetime.utcnow()
            time_min = (now - timedelta(days=days)).isoformat() + 'Z'
            time_max = now.isoformat() + 'Z'

            events_result = self.service.events().list(
                calendarId='primary',
                timeMin=time_min,
                timeMax=time_max,
                singleEvents=True,
                orderBy='startTime'
            ).execute()

            events = events_result.get('items', [])

            meetings = []
            for event in events:
                # Skip non-meetings (e.g., all-day events, reminders)
                if 'dateTime' not in event.get('start', {}):
                    continue

                # Parse start and end times
                start = datetime.fromisoformat(event['start']['dateTime'].replace('Z', '+00:00'))
                end = datetime.fromisoformat(event['end']['dateTime'].replace('Z', '+00:00'))

                duration = int((end - start).total_seconds() / 60)

                # Extract attendees
                attendees = []
                if 'attendees' in event:
                    attendees = [
                        attendee.get('email', '')
                        for attendee in event['attendees']
                        if attendee.get('email')
                    ]

                meeting_data = {
                    'event_id': event['id'],
                    'title': event.get('summary', 'Untitled Meeting'),
                    'start_time': start.replace(tzinfo=None),
                    'end_time': end.replace(tzinfo=None),
                    'duration_minutes': duration,
                    'attendees_emails': attendees,
                    'organizer_email': event.get('organizer', {}).get('email')
                }

                meetings.append(meeting_data)

            logger.info(f"Synced {len(meetings)} meetings for {user_email}")
            return meetings

        except Exception as e:
            logger.error(f"Error syncing calendar meetings: {e}")
            return []

    async def calculate_meeting_time_saved(
        self,
        meetings_before: List[Dict],
        meetings_after: List[Dict]
    ) -> Dict[str, float]:
        """Calculate time saved by reducing meetings"""
        # Calculate total meeting time before and after
        total_before = sum(m['duration_minutes'] for m in meetings_before)
        total_after = sum(m['duration_minutes'] for m in meetings_after)

        time_saved_minutes = total_before - total_after
        time_saved_hours = time_saved_minutes / 60

        # Calculate by meeting type if possible
        meeting_count_before = len(meetings_before)
        meeting_count_after = len(meetings_after)

        return {
            'total_time_saved_minutes': time_saved_minutes,
            'total_time_saved_hours': round(time_saved_hours, 2),
            'meetings_eliminated': meeting_count_before - meeting_count_after,
            'avg_meeting_duration_before': round(total_before / meeting_count_before if meeting_count_before > 0 else 0, 2),
            'avg_meeting_duration_after': round(total_after / meeting_count_after if meeting_count_after > 0 else 0, 2)
        }

    async def analyze_meeting_necessity(self, meeting: Dict, team_context: Dict) -> Dict:
        """
        Use AI to determine if a meeting was necessary
        Based on standup data and async communication
        """
        # Simple heuristic analysis (can be enhanced with AI)
        title = meeting.get('title', '').lower()
        duration = meeting.get('duration_minutes', 0)
        attendee_count = len(meeting.get('attendees_emails', []))

        # Heuristics for unnecessary meetings
        could_be_async = False
        was_necessary = True

        # Short 1-on-1s could often be async
        if duration <= 15 and attendee_count <= 2:
            could_be_async = True

        # Status updates should be async
        if any(keyword in title for keyword in ['standup', 'status', 'update', 'sync']):
            could_be_async = True
            was_necessary = False

        # Long meetings with many people are often necessary
        if duration >= 45 and attendee_count >= 5:
            was_necessary = True
            could_be_async = False

        return {
            'was_necessary': was_necessary,
            'could_be_async': could_be_async,
            'reason': self._get_necessity_reason(title, duration, attendee_count)
        }

    def _get_necessity_reason(self, title: str, duration: int, attendee_count: int) -> str:
        """Generate reason for necessity determination"""
        if 'standup' in title or 'status' in title:
            return "Status meetings can be replaced with async updates"

        if duration <= 15 and attendee_count <= 2:
            return "Short 1-on-1s could be handled via Slack"

        if 'brainstorm' in title or 'planning' in title:
            return "Planning meetings benefit from real-time collaboration"

        if attendee_count >= 5:
            return "Large meetings enable team alignment"

        return "Meeting necessity unclear - could evaluate further"

    async def get_meeting_stats(self, meetings: List[Dict]) -> Dict:
        """Calculate meeting statistics"""
        if not meetings:
            return {
                'total_meetings': 0,
                'total_time_hours': 0,
                'avg_duration_minutes': 0,
                'avg_attendees': 0
            }

        total_time = sum(m['duration_minutes'] for m in meetings)
        total_attendees = sum(len(m.get('attendees_emails', [])) for m in meetings)

        return {
            'total_meetings': len(meetings),
            'total_time_minutes': total_time,
            'total_time_hours': round(total_time / 60, 2),
            'avg_duration_minutes': round(total_time / len(meetings), 2),
            'avg_attendees': round(total_attendees / len(meetings), 2)
        }
