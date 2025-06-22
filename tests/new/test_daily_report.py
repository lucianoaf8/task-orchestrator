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


def test_generate_html_report_counts(monkeypatch):
    gen = dr.DailyReportGenerator.__new__(dr.DailyReportGenerator)
    gen.config_manager = mock.Mock()
    gen.config_manager.get_all_tasks.return_value = {'a':{},'b':{},'c':{}}
    task1 = {
        'task_name': 'a',
        'task_config': {},
        'scheduled_time': datetime(2021,1,1,1,0),
        'execution': {
            'start_time': '2021-01-01T01:00:00',
            'end_time': '2021-01-01T01:05:00',
            'status': 'SUCCESS',
            'retry_count': 0
        }
    }
    task2 = {
        'task_name': 'b',
        'task_config': {},
        'scheduled_time': datetime(2021,1,1,2,0),
        'execution': None
    }
    fail_exec = {
        'start_time': '2021-01-01T03:00:00',
        'end_time': '2021-01-01T03:02:00',
        'status': 'FAILED',
        'retry_count': 1,
        'error': 'boom',
        'exit_code': 1
    }
    task3 = {
        'task_name': 'c',
        'task_config': {},
        'scheduled_time': datetime(2021,1,1,3,0),
        'execution': fail_exec
    }
    monkeypatch.setattr(gen, 'get_tasks_in_timeframe', lambda s,e: [task1, task2, task3])
    monkeypatch.setattr(gen, 'get_failed_tasks_last_24h', lambda: [{'task_name':'c','execution': fail_exec,'execution_time': datetime(2021,1,1,3,0)}])
    html = gen.generate_html_report(datetime(2021,1,1), datetime(2021,1,2))
    assert 'Total Scheduled' in html
    assert '>3<' in html  # total
    assert '>1<' in html  # success count
    assert 'Failed Tasks' in html
