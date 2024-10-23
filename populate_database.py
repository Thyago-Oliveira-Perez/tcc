import os
import subprocess
import logging
from datetime import datetime
import sqlite3
import re
import threading

# Configuração do arquivo de log com a data atual
log_filename = "logs/" + datetime.now().strftime('%Y-%m-%d') + '.log'
logging.basicConfig(filename=log_filename, level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')

# Caminho do repositório Git (subpasta dentro da pasta onde está o script main.py)
# Substitua 'nome_da_pasta_do_projeto' pelo nome correto
repo_path = os.path.join(os.path.dirname(
    os.path.abspath(__file__)), 'kubernetes')


def log_info(message):
    message = f"[INFO] {message}"
    logging.info(f"{message}")
    print(f"{message}")


def log_error(message):
    message = f"[ERROR] {message}"
    logging.error(f"{message}")
    print(f"{message}")


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
            path TEXT PRIMARY KEY
        )
    ''')
    # Cria tabela para armazenar a relacao entre commits e arquivos
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS commits_X_files (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            commit_hash TEXT,
            file_path TEXT,
            FOREIGN KEY (commit_hash) REFERENCES commits(commit_hash),
            FOREIGN KEY (file_path) REFERENCES files(path)
        )
    ''')
    conn.commit()
    log_info("Tabelas validadas no banco de dados.")


# Função para limpar o banco de dados


def drop_tables(conn):
    log_info("Limpando banco de dados...")
    cursor = conn.cursor()
    cursor.execute('DROP TABLE IF EXISTS commits_X_files;')
    cursor.execute('DROP TABLE IF EXISTS commits;')
    cursor.execute('DROP TABLE IF EXISTS files;')
    conn.commit()
    log_info("Banco de dados limpo.")

# Função para resetar o banco de dados


def reset_database():
    conn = connect_db()
    drop_tables(conn)
    create_tables(conn)
    conn.close()

# Função para salvar commits no banco


def save_commits_in_batches(conn, commits):
    log_info(f"Salvando commits em lotes de {len(commits)}")
    try:
        cursor = conn.cursor()
        cursor.executemany('''
            INSERT OR IGNORE INTO commits (commit_hash, author, date, message)
            VALUES (?, ?, ?, ?)
        ''', commits)
        conn.commit()
    except Exception as e:
        log_exception(f"Erro ao salvar commits em lote: {e}")
        conn.rollback()

# Função para salvar um arquivo no banco


def save_files_in_batches(files):
    conn = connect_db()

    for paths in files:

        paths = [(path,) for path in paths]

        log_info(f"Salvando files em lotes de {len(paths)}")
        try:
            cursor = conn.cursor()
            cursor.executemany('''
                INSERT OR IGNORE INTO files (path) VALUES (?)
            ''', paths)
            conn.commit()
        except Exception as e:
            log_exception(f"Erro ao inserir arquivos em lote: {e}")
            conn.rollback()

    conn.close()


# Função para salvar as relações entre commits e arquivos


def save_files_X_commits_relation_in_batches(conn, relations):
    log_info(f"Salvando relação em lotes de {len(relations)}")
    try:
        cursor = conn.cursor()
        cursor.executemany('''
            INSERT OR IGNORE INTO commits_X_files (commit_hash, file_path)
            VALUES (?, ?)
        ''', relations)
        conn.commit()
    except Exception as e:
        log_exception(f"Erro ao inserir relações em lote: {e}")
        conn.rollback()

# Função para extrair o commits do log retornado pelo comando "git log"


def extract_commits_from_log(file_path, log):
    try:
        # Usar uma regex para identificar corretamente as linhas que começam com commit seguido de um hash válido
        commit_regex = re.compile(r'^commit [0-9a-f]{40}', re.MULTILINE)

        # Encontrar todos os commits no log
        matches = list(commit_regex.finditer(log))

        if not matches:
            log_info(
                f"Nenhum commit encontrado no log para o arquivo {file_path}")
            return None

        return matches
    except Exception as e:
        log_exception(f"Erro ao salvar logs no banco de dados: {e}")

# Fução para extrair objeto commit do log


def extract_commit(i, matches, log):
    try:
        # Captura o início de cada commit
        start_pos = matches[i].start()

        # Se houver mais commits, capture o final até o próximo commit; caso contrário, vá até o final do log
        end_pos = matches[i+1].start() if i+1 < len(matches) else len(log)

        # Extrai o texto do commit
        commit_text = log[start_pos:end_pos].strip()

        # Agora extraímos as partes do commit (hash, autor, data, mensagem)
        lines = commit_text.split('\n')

        if len(lines) < 5:
            return None

        commit_hash = lines[0].replace('commit', '').strip()
        if lines[1].startswith('Author: '):
            author = lines[1].replace('Author:', '').strip()
            date = lines[2].replace('Date:', '').strip()
        else:
            author = lines[2].replace('Author:', '').strip()
            date = lines[3].replace('Date:', '').strip()
        message = "\n".join([line.strip() for line in lines[4:]]).strip()

        return {
            'commit_hash': commit_hash,
            'author': author,
            'date': date,
            'message': message
        }
    except Exception as e:
        log_exception(f"Erro ao extrair commits do log: {e}")


# Função para a relação entre arquivos e commits


def get_file_X_commit_relation(file_path, log):
    matches = extract_commits_from_log(file_path, log)
    if not matches:
        return None

    commits = []

    # Percorrer os commits identificados
    for i in range(len(matches)):
        result = extract_commit(i, matches, log)

        commit_hash = result['commit_hash']

        commits.append(commit_hash)

    return {
        'path': file_path,
        'commits': commits
    }

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

# Função para salvar todos os commits do repostorio


def save_all_commits(path):
    try:
        log_info(
            f"Processando todos os commits no repositório: {path}")
        log = get_git_log(path)

        if log is None:
            log_info(
                f"Este repositório não contem logs de commit: {path}")

        # Encontrar todos os commits no log
        matches = extract_commits_from_log(path, log)

        commits = []

        # Percorrer os commits identificados
        for i in range(len(matches)):
            result = extract_commit(i, matches, log)

            commit_hash = result['commit_hash']
            author = result['author']
            date = result['date']
            message = result['message']

            commits.append((commit_hash, author, date, message))

        chunks = [commits[i:i + 1000] for i in range(0, len(commits), 1000)]

        conn = connect_db()
        for chunk in chunks:
            save_commits_in_batches(conn, chunk)
        conn.close()

    except Exception as e:
        log_exception(f"Error: {e}")

# Função para processar logs


def process_logs(files):
    relations = []

    for paths in files:
        for path in paths:
            log = get_git_log(path)

            if log is None:
                log_info(
                    f"Este arquivo não contem logs de commit: {path}")
                continue

            file_relation = get_file_X_commit_relation(path, log)
            relations.append(file_relation)

    data = []

    for relation in relations:
        for commit in relation['commits']:
            data.append((commit, relation['path']))

    conn = connect_db()
    save_files_X_commits_relation_in_batches(conn, data)
    conn.close()

# Função para salvar todos os arquivos


def save_all_files():
    file_paths = []
    # Percorre todos os arquivos do repositório
    log_info("Processando todos os arquivos do repositório...")
    for root, _, files in os.walk(repo_path):
        for file in files:
            file_path = os.path.join(root, file)
            if '.git' not in file_path and file != 'main.py':  # Ignora a pasta .git e o próprio script
                file_paths.append(file_path)

    log_info(f"Salvando {len(file_paths)} arquivos...")

    chunks = [file_paths[i:i + 1000] for i in range(0, len(file_paths), 1000)]

    # Criando uma lista de threads
    threads = []

    chunks_files = [chunks[i:i + 5] for i in range(0, len(chunks), 5)]

    # Criando e iniciando 5 threads
    for chunk_file in chunks_files:
        thread = threading.Thread(
            target=save_files_in_batches, args=([chunk_file]))
        threads.append(thread)
        thread.start()

    # Aguardando todas as threads terminarem
    for thread in threads:
        thread.join()

    return file_paths

# Função para salvar todas as relações entre arquivos e commits


def save_all_relations(file_paths):
    chunks = [file_paths[i:i + 1000] for i in range(0, len(file_paths), 1000)]

    # Criando uma lista de threads
    threads = []

    chunks_files = [chunks[i:i + 5] for i in range(0, len(chunks), 5)]

    # Criando e iniciando 5 threads
    for chunk_file in chunks_files:
        thread = threading.Thread(target=process_logs, args=([chunk_file]))
        threads.append(thread)
        thread.start()

    # Aguardando todas as threads terminarem
    for thread in threads:
        thread.join()

# Função principal para percorrer os arquivos do repositório


def run():
    try:
        save_all_commits(repo_path)
        file_paths = save_all_files()
        save_all_relations(file_paths)
    except Exception as e:
        log_exception(f"Erro: {e}")


if __name__ == "__main__":
    while 1:
        option = (input('Limpar banco de dados (s/n)? ')).lower()

        if option == 's':
            reset_database()
            break
        elif option == 'n':
            break
        else:
            print("Opção inválida, voltando ao menu principal...")
            os.system('cls' if os.name == 'nt' else 'clear')

    log_info("Iniciando processo de captura de logs do repositório.")

    run()

    log_info("Processo finalizado.")
