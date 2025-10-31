#!/usr/bin/env python3
from __future__ import annotations
import os, sys, json, time
import requests

API = os.getenv('API_URL', 'http://localhost:8000')
USER = os.getenv('ADMIN_USER', 'admin')
PASS = os.getenv('ADMIN_PASS', 'admin')
REASON = os.getenv('X_REASON', 'seed-demo')

headers = {'X-Reason': REASON}

def login() -> str:
    r = requests.post(f'{API}/auth/login', json={'username': USER, 'password': PASS}, headers=headers)
    r.raise_for_status()
    token = r.json()['access_token']
    return token

 def auth_headers(token: str):
    return {**headers, 'Authorization': f'Bearer {token}'}

def ensure_store(token: str, code: str, name: str) -> int:
    r = requests.get(f'{API}/stores', headers=auth_headers(token))
    r.raise_for_status()
    stores = r.json()
    for s in stores:
        if s.get('code') == code:
            return s['id']
    r = requests.post(f'{API}/stores', json={'code': code, 'name': name}, headers=auth_headers(token))
    r.raise_for_status()
    return r.json()['id']

def create_device(token: str, store_id: int, sku: str, name: str):
    payload = {'sku': sku, 'name': name, 'categoria': 'iPhone', 'condicion': 'B'}
    r = requests.post(f'{API}/stores/{store_id}/devices', json=payload, headers=auth_headers(token))
    r.raise_for_status()

if __name__ == '__main__':
    t = login()
    s1 = ensure_store(t, 'CENTRO', 'Centro')
    s2 = ensure_store(t, 'NORTE', 'Norte')
    create_device(t, s1, 'IP12-64-B', 'iPhone 12 64GB B')
    create_device(t, s1, 'IP13PM-128-B', 'iPhone 13 Pro Max 128GB B')
    create_device(t, s2, 'IP14P-256-A', 'iPhone 14 Pro 256GB A')
    print('Seed ok')
