from datetime import datetime, timedelta
from unittest import mock

import scripts.notifications.daily_report as dr

class DummyCM:
    def __init__(self):
        self.tasks={'t':{'schedule':'0 0 * * *','type':'shell','command':'c','timeout':0,'retry_count':0,'retry_delay':0,'dependencies':[], 'enabled':True}}
        self.history=[{'start_time':(datetime.now()-timedelta(hours=1)).isoformat(), 'end_time':datetime.now().isoformat(), 'status':'SUCCESS', 'retry_count':0}]
    def get_all_tasks(self):
        return self.tasks
    def get_task_history(self,name,limit):
        return self.history
    def get_credential(self,name):
        return 'u'
    def get_config(self,section,key,default=None):
        if key=='daily_report_recipients':
            return '["a"]'
        return default

class DummySMTP:
    def __init__(self,*a,**k):
        pass
    def __enter__(self):
        return self
    def __exit__(self,*a):
        pass
    def starttls(self):
        pass
    def login(self,u,p):
        pass
    def send_message(self,msg):
        self.sent=msg


def test_generate_and_send(monkeypatch):
    gen = dr.DailyReportGenerator.__new__(dr.DailyReportGenerator)
    gen.config_manager = DummyCM()
    monkeypatch.setattr(dr, 'croniter', lambda s,start: mock.MagicMock(get_next=lambda cls: datetime.now()))
    monkeypatch.setattr(dr.smtplib,'SMTP', DummySMTP)
    html = gen.generate_html_report(datetime.now()-timedelta(hours=1), datetime.now())
    assert 'Daily Task Report' in html
    assert gen.send_daily_report()
