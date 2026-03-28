import os
import glob
import re

def repair_ghost_comments(directory):
    html_files = glob.glob(os.path.join(directory, '**', '*.html'), recursive=True)
    count_repaired = 0
    
    # Procura `{#` seguido por qualquer coisa que tenha ARQUIVO: ou POR QUE ELE EXISTE: fechando com `#}`
    pattern = re.compile(r'{#\s*(?:ARQUIVO:|POR QUE ELE EXISTE:)[\s\S]*?#}', re.IGNORECASE)
    
    for file_path in html_files:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            if pattern.search(content):
                def replacement(match):
                    original_comment = match.group(0)
                    # Corta o {# e o #}
                    inner_content = original_comment[2:-2]
                    # Transforma no real multi-line comment do Django
                    return f"{{% comment %}}{inner_content}{{% endcomment %}}"
                
                new_content = pattern.sub(replacement, content)
                
                # Vamos também garantir que o {{% comment %}} não mate a tag de extends, 
                # Movendo o comment block pra DEPOIS do extends, se o extends existir logo na linha 2?
                # Na verdade, em Django, o extends DEVE ser a PRIMEIRA tag do arquivo. 
                # Meu script injetou comentários antes do extends, o que causa TemplateSyntaxError!
                # VAMOS CONSERTAR O POSICIONAMENTO:
                
                # Se {% extends ... %} existe, ele DEVE ir pra linha 1.
                extends_match = re.search(r'{% extends [^}]+%}', new_content)
                if extends_match:
                    extends_tag = extends_match.group(0)
                    # remove o extends de onde está
                    new_content = new_content.replace(extends_tag, '', 1)
                    # enfia no master_top
                    new_content = extends_tag + '\n' + new_content.lstrip()
                
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(new_content)
                    
                count_repaired += 1
                
        except Exception as e:
            print(f"Erro em {file_path}: {e}")

    print("====================================")
    print(" GHOST WRITING REPAIR SQUAD  ")
    print("====================================")
    print(f"Total varrido e corrigido para Secure Jinja Syntax (comment tag): {count_repaired} views.")

if __name__ == '__main__':
    templates_dir = os.path.join(os.path.dirname(__file__), 'templates')
    repair_ghost_comments(templates_dir)
