import sys

def extract_traceback():
    try:
        with open('server_log.txt', 'r', encoding='utf-16le', errors='replace') as f:
            lines = f.readlines()
        
        print("Lendo as últimas 150 linhas do log:")
        for line in lines[-150:]:
            print(line.rstrip())
            
    except Exception as e:
        print(f"Erro ao ler log: {e}")

if __name__ == '__main__':
    extract_traceback()
