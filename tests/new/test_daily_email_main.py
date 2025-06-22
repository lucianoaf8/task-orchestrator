from types import SimpleNamespace
from unittest import mock

import scripts.notifications.daily_email_main as dem

class DummyCM:
    def __init__(self):
        self.cred={'sf_access_token':'tok','email_username':'u','email_password':'p'}
        self.cfg={'salesforce':{'instance_url':'http://s'},'email':{'smtp_server':'s','smtp_port':'25','recipients':'["a"]'}}
    def get_credential(self,name):
        return self.cred.get(name)
    def get_config(self,section,key,default=None):
        return self.cfg.get(section,{}).get(key,default)

def test_get_config_value_env(monkeypatch):
    cm=DummyCM()
    monkeypatch.setenv('EMAIL_SMTP_SERVER','env')
    assert dem.get_config_value(cm,'email','smtp_server')=='env'


def test_fetch_build_send(monkeypatch):
    cm=DummyCM()
    resp=mock.Mock(status_code=200, json=lambda:{'records':[{'total':1}]})
    monkeypatch.setattr(dem.requests,'get',lambda *a,**k: resp)
    body=dem.build_email_body({'records':[{'total':2}]})
    assert '2' in body
    class DummySMTP:
        def __init__(self,*a,**k):
            self.starttls_called=False
        def __enter__(self):
            return self
        def __exit__(self,*a):
            pass
        def starttls(self):
            self.starttls_called=True
        def login(self,u,p):
            pass
        def send_message(self,msg):
            self.msg=msg

    monkeypatch.setattr(dem.smtplib,'SMTP', DummySMTP)
    dem.send_email(cm,'body')

import pytest


def test_fetch_salesforce_data_success(monkeypatch):
    cm = DummyCM()
    resp = mock.Mock(status_code=200, json=lambda: {'ok': True})
    monkeypatch.setattr(dem.requests, 'get', lambda *a, **k: resp)
    data = dem.fetch_salesforce_data(cm)
    assert data == {'ok': True}


def test_fetch_salesforce_data_missing(monkeypatch):
    cm = DummyCM()
    cm.cfg['salesforce']['instance_url'] = None
    with pytest.raises(RuntimeError):
        dem.fetch_salesforce_data(cm)


def test_fetch_salesforce_data_error(monkeypatch):
    cm = DummyCM()
    def raise_err(*a, **k):
        raise dem.RequestException('bad')
    monkeypatch.setattr(dem.requests, 'get', raise_err)
    with pytest.raises(RuntimeError):
        dem.fetch_salesforce_data(cm)
