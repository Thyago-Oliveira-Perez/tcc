import subprocess
import os
import sys


def save_git_history_for_directory(directory):
    # Verifica se o diretório é um repositório git
    if not os.path.isdir(directory):
        print(f"Diretório '{directory}' não encontrado.")
        return

    if not os.path.isdir(os.path.join(directory, ".git")):
        print(f"Diretório '{directory}' não é um repositório git.")
        return

    # Percorre todos os arquivos no diretório
    for root, _, files in os.walk(directory):
        for file in files:
            file_path = os.path.join(root, file)
            log_file = f"./kubernetes_logs/{file_path}.log"

            print(root)

            if "\\.git\\" in root:
                continue

            try:
                # git_log_command = f"cd {directory} ; git log --pretty=format:\"%h - %an, %ad : %s\" -- {file_path}"

                # git_log = subprocess.check_output(
                #     git_log_command, cwd=directory, text=True)
                # print(f"{file_path} log lenght: ", len(git_log))
                # # Salva o histórico em um arquivo .log
                # with open(log_file, "w") as log:
                #     log.write(git_log)

                print(f"Histórico de alterações salvo em '{log_file}'.")

            except subprocess.CalledProcessError as e:
                print(
                    f"Erro ao executar o comando git para '{file_path}': {e}")


def tryin(directory):
    # Percorre todos os arquivos no diretório
    for root, _, files in os.walk(directory):
        for file in files:
            file_path = os.path.join(root, file)
            log_file = f"./kubernetes_logs/{file_path}.log"

            if "\\.git\\" in root:
                continue

            try:
                # command = f"git log --pretty=format:\"%h - %an, %ad : %s\" -- ./{file}"
                command = f"git log --pretty=format:\"%h - %an, %ad : %s\" -- ./{file}"
                print(f"root folder: {root}\nfile: {file}\ncommand: {command}")
                # Run the command and capture the output
                output = subprocess.check_output(
                    command, shell=True, text=True)

                # Print the command output
                print("Command output:")
                print(output)
                # git_log_command = f"cd {directory} ; git log --pretty=format:\"%h - %an, %ad : %s\" -- {file}"

                # git_log = subprocess.check_output(
                #     git_log_command, cwd=directory, text=True)
                # print(f"{file_path} log lenght: ", len(git_log))
                # # Salva o histórico em um arquivo .log
                # with open(log_file, "w") as log:
                #     log.write(git_log)

                # print(f"Histórico de alterações salvo em '{log_file}'.")

            except subprocess.CalledProcessError as e:
                print(
                    f"Erro ao executar o comando git para '{file_path}': {e}")


if __name__ == "__main__":
    tryin("./kubernetes")
