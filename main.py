import os
import subprocess
import shutil
import logging
from datetime import datetime

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

# Função para obter o log de um arquivo
def get_git_log(file_path):
    try:
        result = subprocess.run(['git', 'log', '--', file_path], cwd=repo_path,
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if result.returncode == 0:
            log_info(
                f"Log capturado com sucesso para o arquivo: {file_path}")
            return result.stdout
        else:
            log_error(
                f"Erro ao obter o log de {file_path}: {result.stderr}")
            return f"Erro ao obter o log de {file_path}: {result.stderr}"
    except Exception as e:
        log_exception(
            f"Erro ao executar o comando git log para o arquivo {file_path}: {e}")
        return f"Erro ao executar o comando git log para o arquivo {file_path}: {e}"

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
def save_git_logs():
    try:
        # Verifica se a pasta de logs já existe
        if os.path.exists(logs_folder):
            # Apaga a pasta de logs anterior se já existir
            shutil.rmtree(logs_folder)
            log_info(f"Pasta de logs existente apagada: {logs_folder}")
        os.makedirs(logs_folder)
        log_info(f"Pasta de logs criada: {logs_folder}")

        # Percorre todos os arquivos do repositório
        for root, _, files in os.walk(repo_path):
            for file in files:
                file_path = os.path.join(root, file)
                if '.git' not in file_path and file != 'main.py':  # Ignora a pasta .git e o próprio script
                    log_info(f"Processando arquivo: {file_path}")
                    log = get_git_log(file_path)
                    log_file_path = create_log_folder_structure(file_path)

                    if log is None:
                        log_info(
                            f"Arquivo ignorado por não conter log de alterações: {log_file_path}")
                        continue

                    # Salva o log no arquivo correspondente
                    with open(log_file_path, 'w', encoding='utf-8') as log_file:
                        log_file.write(log)
                    log_info(f"Log salvo em: {log_file_path}")
    except Exception as e:
        log_exception(f"Erro ao salvar os logs do repositório: {e}")


if __name__ == "__main__":
    log_info("Iniciando processo de captura de logs do repositório.")
    save_git_logs()
    log_info("Processo finalizado.")
