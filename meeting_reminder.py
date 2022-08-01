from O365 import Account, FileSystemTokenBackend
from datetime import datetime, timedelta
import os
import time

class MeetingReminder():
    def __init__(self):
        self.auth_client_id = os.environ['O365_CLIENT_ID']
        self.auth_client_secret = os.environ['O365_CLIENT_SECRET']
        self.auth_tenant_id= os.environ['O365_TENANT_ID']
        token_backend = FileSystemTokenBackend(token_path='ignore', token_filename='o365_token.txt')
        self.account = Account((self.auth_client_id, self.auth_client_secret), token_backend=token_backend, tenant_id=self.auth_tenant_id)
        if not self.account.is_authenticated:
            if self.account.authenticate(scopes=['basic', 'calendar']):
                print('Authenticated!')
        self.calendar = self.account.schedule().get_default_calendar()
        self.day_names = ['Lundi' , 'Mardi', 'Mercredi', 'Jeudi', 'Vendredi', 'Samedi', 'Dimanche']
    
    def get_next_meeting_events(self):
        date_time = datetime.fromtimestamp(time.time())
        query = self.calendar.new_query('start').greater_equal(date_time)
        query.chain('and').on_attribute('end').less_equal(date_time + timedelta(days=6))
        events = self.calendar.get_events(query=query)
        return [event for event in events if not event.is_cancelled and "Daily Sprint" not in event.subject]
            
    def meeting_event_to_str(self, meeting_event):
        locations = ''
        for location in meeting_event.locations:
            locations += location['displayName'] + ' '
        
        today_date = datetime.today().date()
        if meeting_event.start.date() == today_date:
            start_date_str = 'Aujourd\'hui'
        elif meeting_event.start.date() == today_date + timedelta(days=1):
            start_date_str = 'Demain'
        else:
            start_date_str = self.day_names[meeting_event.start.date().weekday()] + ' ' + meeting_event.start.date().strftime("%d/%m")
        
        if meeting_event.start.date() == meeting_event.end.date():
            return '{} {} à {} {}, {}'.format(start_date_str,
                                                    meeting_event.start.time().strftime("%H:%M"),
                                                    meeting_event.end.time().strftime("%H:%M"),
                                                    meeting_event.subject,
                                                    locations)

if '__main__' == __name__:
    meeting_reminder = MeetingReminder()
    meeting_reminder.get_next_meeting_events()