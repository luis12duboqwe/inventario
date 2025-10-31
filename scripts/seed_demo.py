#!/usr/bin/env python3
from __future__ import annotations
import os, requests

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


def create_device(token: str, store_id: int, sku: str, name: str, categoria: str = 'iPhone', condicion: str = 'B'):
    payload = {'sku': sku, 'name': name, 'categoria': categoria, 'condicion': condicion}
    r = requests.post(f'{API}/stores/{store_id}/devices', json=payload, headers=auth_headers(token))
    r.raise_for_status()


if __name__ == '__main__':
    t = login()
    s1 = ensure_store(t, 'CENTRO', 'Centro')
    s2 = ensure_store(t, 'NORTE', 'Norte')

    MODELOS = [
        ('IP11-64-B', 'iPhone 11 64GB B', 'iPhone', 'B'),
        ('IP12-64-B', 'iPhone 12 64GB B', 'iPhone', 'B'),
        ('IP12PM-128-B', 'iPhone 12 Pro Max 128GB B', 'iPhone', 'B'),
        ('IP13P-128-A', 'iPhone 13 Pro 128GB A', 'iPhone', 'A'),
        ('IP13PM-256-B', 'iPhone 13 Pro Max 256GB B', 'iPhone', 'B'),
        ('IP14P-256-A', 'iPhone 14 Pro 256GB A', 'iPhone', 'A'),
        ('IP14PM-256-A', 'iPhone 14 Pro Max 256GB A', 'iPhone', 'A'),
        ('IP15P-256-A', 'iPhone 15 Pro 256GB A', 'iPhone', 'A'),
        ('IP15PM-256-A', 'iPhone 15 Pro Max 256GB A', 'iPhone', 'A'),
    ]

    for sku,name,cat,cond in MODELOS:
        try:
            create_device(t, s1, sku, name, cat, cond)
        except Exception:
            pass

    print('Seed ok')
