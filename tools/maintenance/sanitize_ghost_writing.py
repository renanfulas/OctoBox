import os
import glob
import re

def obscure_architectural_ghosts(directory):
    html_files = glob.glob(os.path.join(directory, '**', '*.html'), recursive=True)
    count_infected = 0
    
    # Regex para dar "Match" num Comentário HTML Clássico que tenha nossas documentações
    # Queremos pegar `<!--` seguido de espaço/quebras, algo com "ARQUIVO:" ou "POR QUE", fechando com `-->`
    
    # A maneira mais segura de substituir esses Ghosts espcíficos que nós mesmos criamos é achar o padrão deles no inicio.
    pattern = re.compile(r'<!--\s*(?:ARQUIVO:|POR QUE ELE EXISTE:)[\s\S]*?-->', re.IGNORECASE)
    
    for file_path in html_files:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Checa se existe a assinatura
            if pattern.search(content):
                # Substituir as pontas
                def replacement(match):
                    original_comment = match.group(0)
                    # Corta o <!-- e o --> e veste com {# e #}
                    # O Django Server vai deletar pro cliente final.
                    inner_content = original_comment[4:-3]
                    return f"{{#{inner_content}#}}"
                
                new_content = pattern.sub(replacement, content)
                
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(new_content)
                    
                count_infected += 1
                
        except Exception as e:
            print(f"Erro em {file_path}: {e}")

    print("====================================")
    print(" GHOST WRITING EXTERMINATION SQUAD  ")
    print("====================================")
    print(f"Total varrido e convertido para Secure Jinja Syntax: {count_infected} views L7.")
    print("O Navegador do Usuário agora enxerga 0% da nossa Arquitetura.")

if __name__ == '__main__':
    templates_dir = os.path.join(os.path.dirname(__file__), 'templates')
    obscure_architectural_ghosts(templates_dir)
