import os
import subprocess
import shutil
import logging
from datetime import datetime
import sqlite3
import re

# Configuração do arquivo de log com a data atual
log_filename = datetime.now().strftime('%Y-%m-%d') + '.log'
logging.basicConfig(filename=log_filename, level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')

# Caminho do repositório Git (subpasta dentro da pasta onde está o script main.py)
# Substitua 'nome_da_pasta_do_projeto' pelo nome correto
repo_path = os.path.join(os.path.dirname(
    os.path.abspath(__file__)), 'kubernetes')

# Caminho para a pasta externa onde os logs serão salvos
logs_folder = os.path.join(repo_path, '..', 'kubernetes_logs')

# Funções para registrar o log


def log_info(message):
    message = f"[INFO] {message}"
    logging.info(f"{message}")
    print(f"{message}")

# Função para registrar o erro


def log_error(message):
    message = f"[ERROR] {message}"
    logging.error(f"{message}")
    print(f"{message}")


# Função para registrar a exceção


def log_exception(message):
    message = f"[EXCEPTION] {message}"
    logging.exception(f"{message}")
    print(f"{message}")

# Função para conectar ao banco de dados SQLite


def connect_db():
    log_info("Conectando ao banco de dados...")
    db_path = os.path.join(repo_path, '..', 'kubernetes_logs.db')
    conn = sqlite3.connect(db_path)
    log_info("Conectado ao banco de dados.")
    return conn

# Função para criar as tabelas no banco de dados


def create_tables(conn):
    cursor = conn.cursor()
    log_info("Validando tabelas no banco de dados...")
    # Cria tabela para armazenar commits
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS commits (
            commit_hash TEXT PRIMARY KEY,
            author TEXT,
            date TEXT,
            message TEXT
        )
    ''')
    # Cria tabela para armazenar arquivos
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS files (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            path TEXT
        )
    ''')
    # Cria tabela para armazenar a relacao entre commits e arquivos
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS commits_X_files (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            commit_hash TEXT,
            file_id INTEGER,
            FOREIGN KEY (commit_hash) REFERENCES commits(commit_hash),
            FOREIGN KEY (file_id) REFERENCES commits(id)
        )
    ''')
    conn.commit()
    log_info("Tabelas validadas no banco de dados.")


# Função para limpar o banco de dados


def drop_tables(conn):
    log_info("Limpando banco de dados...")
    cursor = conn.cursor()
    cursor.execute('DROP TABLE IF EXISTS logs;')
    cursor.execute('DROP TABLE IF EXISTS files;')
    conn.commit()
    log_info("Banco de dados limpo.")

# Função para salvar um arquivo no banco


def insert_file(conn, path):
    log_info(f"Salvando arquivo no banco: {path}")
    cursor = conn.cursor()
    cursor.execute(f"INSERT INTO files (path) VALUES ('{path}')")
    conn.commit()
    return cursor.lastrowid

# Função para salvar um log no banco


def insert_commit(conn, commit_hash, author, date, message):
    log_info(f"Salvando commit no banco: {commit_hash}")
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO commits (commit_hash, author, date, message)
        VALUES (?, ?, ?, ?)
    ''', (commit_hash, author, date, message))
    conn.commit()
    log_info(f"Commit salvo no banco de dados: {commit_hash}")


def insert_relation(conn, commit_hash, file_id):
    log_info(f"Salvando relacao no banco de dados: {commit_hash} e {file_id}")
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO commits_X_files (commit_hash, file_id)
        VALUES (?, ?)
    ''', (commit_hash, file_id))
    conn.commit()
    log_info(f"Relacao salva no banco de dados: {commit_hash} e {file_id}")


def exist_commit_by_commit_hash(conn, commit_hash):
    cursor = conn.cursor()
    cursor.execute(f"SELECT commit_hash FROM commits WHERE commit_hash = '{commit_hash}'")
    
    result = cursor.fetchone()  # Recupera o primeiro resultado
    
    if result:
        return result[0]
    else:
        log_info("Commit não encontrado")
        return None


def exist_file_by_path(conn, path):
    cursor = conn.cursor()
    cursor.execute(f"SELECT id FROM files WHERE path = '{path}'")
    
    result = cursor.fetchone()  # Recupera o primeiro resultado
    
    if result:
        return result[0]
    else:
        log_info("File não encontrado")
        return None

# Função para processar e salvar commits no banco de dados
def process_and_save_logcommitn_db(file_path, log):
    conn = connect_db()

    try:
        # Usar uma regex para identificar corretamente as linhas que começam com commit seguido de um hash válido
        commit_regex = re.compile(r'(commit [0-9a-f]{40})')

        # Encontrar todos os commits no log
        matches = list(commit_regex.finditer(log))

        if not matches:
            log_info(
                f"Nenhum commit encontrado no log para o arquivo {file_path}")
            return

        # Percorrer os commits identificados
        for i in range(len(matches)):
            # Captura o início e o fim de cada commit no log
            start_pos = matches[i].start()
            end_pos = matches[i+1].start() if i+1 < len(matches) else len(log)

            # Extrai o texto do commit
            commit_text = log[start_pos:end_pos].strip()

            # Agora extraímos as partes do commit (hash, autor, data, mensagem)
            lines = commit_text.split('\n')

            if len(lines) < 5:
                continue

            commit_hash = lines[0].replace('commit', '').strip()
            author = lines[1].replace('Author:', '').strip()
            date = lines[2].replace('Date:', '').strip()
            message = "\n".join([line.strip() for line in lines[4:]]).strip()

            commit = exist_commit_by_commit_hash(conn, commit_hash)

            if commit is None:
               insert_commit(conn, commit_hash, author, date, message)
            
            file = exist_file_by_path(conn, file_path)

            if file is None:
                file_id = insert_file(conn, file_path)
                insert_relation(conn, commit_hash, file_id)
            else:
                insert_relation(conn, commit_hash, file)


    except Exception as e:
        log_exception(f"Erro ao salvar logs no banco de dados: {e}")

    finally:
        conn.close()

# Função para obter o log de um arquivo


# Função para capturar logs sem confundir a palavra "commit" em comentários
def get_git_log(file_path):
    try:
        result = subprocess.run(
            ['git', 'log', '--', file_path],
            cwd=repo_path,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding='utf-8',  # Forçar UTF-8 na leitura
            errors='replace'  # Substituir caracteres inválidos
        )
        if result.returncode == 0:
            log_info(f"Log capturado com sucesso para o arquivo: {file_path}")
            return result.stdout
        else:
            log_error(f"Erro ao obter o log de {file_path}: {result.stderr}")
            return f"Erro ao obter o log de {file_path}: {result.stderr}"
    except Exception as e:
        log_exception(
            f"Erro ao executar o comando git log para o arquivo {file_path}: {e}")
        return f"Erro ao executar o comando git log para o arquivo {file_path}: {e}"

# Função para salvar o log no arquivo correspondente com tratamento de encoding


def save_logcommitle(log_file_path, log):
    try:
        with open(log_file_path, 'w', encoding='utf-8', errors='replace') as log_file:
            log_file.write(log)
        log_info(f"Log salvo em: {log_file_path}")
    except Exception as e:
        log_exception(f"Erro ao salvar o log no arquivo {log_file_path}: {e}")

# Função para criar a estrutura de pastas para os logs


def create_log_folder_structure(file_path):
    # Caminho relativo ao repositório
    relative_path = os.path.relpath(file_path, repo_path)
    log_file_path = os.path.join(
        logs_folder, relative_path) + '.log'  # Nome do arquivo .log
    log_folder = os.path.dirname(log_file_path)  # Pasta onde o log será salvo

    if not os.path.exists(log_folder):
        os.makedirs(log_folder)
        log_info(f"Pasta de log criada: {log_folder}")

    return log_file_path

# Função principal para percorrer os arquivos do repositório


def run():
    try:
        # Percorre todos os arquivos do repositório
        for root, _, files in os.walk(repo_path):
            for file in files:
                file_path = os.path.join(root, file)
                if '.git' not in file_path and file != 'main.py':  # Ignora a pasta .git e o próprio script
                    log_info(f"Processando arquivo: {file_path}")
                    log = get_git_log(file_path)

                    if log is None:
                        log_info(f"Este arquivo não contem logs de commit: {file_path}")
                        continue

                    # Processa e salva os logs no banco de dados
                    process_and_save_logcommitn_db(file_path, log)
    except Exception as e:
        log_exception(f"Erro ao salvar os logs do repositório: {e}")


if __name__ == "__main__":
    while 1:
        option = input('Limpar banco de dados (s/n)? ')

        if option == 's':
            conn = connect_db()
            drop_tables(conn)
            create_tables(conn)
            conn.close()
            break
        elif option == 'n':
            break
        else:
            print("Opção inválida, voltando ao menu principal...")
            os.system('cls' if os.name == 'nt' else 'clear')

    log_info("Iniciando processo de captura de logs do repositório.")

    run()

    log_info("Processo finalizado.")
