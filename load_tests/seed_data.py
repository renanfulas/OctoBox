"""
Gera CSVs sintéticos para testes de import e carga.
Uso:
  python load_tests/seed_data.py --rows 10000 --out students_seed.csv

Gera um CSV com colunas: id,name,email,phone,created_at
"""
import csv
import argparse
import random
import string
from datetime import datetime, timedelta

FIRST_NAMES = ['Ana','Bruno','Carlos','Daniela','Eduardo','Fernanda','Gustavo','Helena','Igor','Julia']
LAST_NAMES = ['Silva','Santos','Oliveira','Souza','Pereira','Costa','Almeida','Ribeiro']

def random_name():
    return f"{random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)}"

def random_email(name, idx):
    base = ''.join(c for c in name.lower() if c.isalpha())
    return f"{base}.{idx}@example.com"

def random_phone():
    return f"55{random.randint(10,99)}9{random.randint(10000000,99999999)}"

def random_date(start_days=365*3):
    days_ago = random.randint(0, start_days)
    dt = datetime.utcnow() - timedelta(days=days_ago, seconds=random.randint(0,86400))
    return dt.isoformat() + 'Z'

def generate_csv(path, rows):
    with open(path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['id','name','email','phone','created_at'])
        for i in range(1, rows+1):
            name = random_name()
            email = random_email(name, i)
            phone = random_phone()
            created_at = random_date()
            writer.writerow([i, name, email, phone, created_at])

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Gera CSVs sintéticos para testes')
    parser.add_argument('--rows', type=int, default=1000, help='Número de linhas')
    parser.add_argument('--out', type=str, default='students_seed.csv', help='Arquivo de saída')
    args = parser.parse_args()
    print(f'Gerando {args.rows} linhas em {args.out}...')
    generate_csv(args.out, args.rows)
    print('Concluído.')
