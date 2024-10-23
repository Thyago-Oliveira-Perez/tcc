import os
import sqlite3
import logging
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

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

# Função para obter os dados ordenados por data


def get_data(conn):
    query = """
    WITH Top10Files AS (
        SELECT
            f.path AS file_path,
            COUNT(cxf.commit_hash) AS total_commits,
            COUNT(*) FILTER (WHERE LOWER(c.message) LIKE '%fix%' 
                            OR LOWER(c.message) LIKE '%hotfix%' 
                            OR LOWER(c.message) LIKE '%resolve%' 
                            OR LOWER(c.message) LIKE '%solve%') AS num_error_commits,
            COUNT(*) FILTER (WHERE LOWER(c.message) LIKE '%refact%' 
                            OR LOWER(c.message) LIKE '%refactor%' 
                            OR LOWER(c.message) LIKE '%rewrite%' 
                            OR LOWER(c.message) LIKE '%improve%' 
                            OR LOWER(c.message) LIKE '%remake%' 
                            OR LOWER(c.message) LIKE '%recode%') AS num_refact_commits
        FROM 
            commits_X_files cxf
        JOIN 
            commits c ON cxf.commit_hash = c.commit_hash
        JOIN 
            files f ON cxf.file_path = f.path
        GROUP BY 
            f.path
        ORDER BY 
            num_error_commits DESC
        LIMIT 10
    )
    SELECT 
        f.path, 
        c.date, 
        CASE
            WHEN LOWER(c.message) LIKE '%fix%' 
                OR LOWER(c.message) LIKE '%hotfix%' 
                OR LOWER(c.message) LIKE '%resolve%' 
                OR LOWER(c.message) LIKE '%solve%' 
            THEN 'erro'
            WHEN LOWER(c.message) LIKE '%refact%' 
                OR LOWER(c.message) LIKE '%refactor%' 
                OR LOWER(c.message) LIKE '%rewrite%' 
                OR LOWER(c.message) LIKE '%improve%' 
                OR LOWER(c.message) LIKE '%remake%' 
                OR LOWER(c.message) LIKE '%recode%' 
            THEN 'refatoracao'
            ELSE 'outro'
        END AS tipo_commit
    FROM 
        commits c
    JOIN 
        commits_X_files cf ON c.commit_hash = cf.commit_hash
    JOIN 
        files f ON f.path = cf.file_path
    WHERE 
        f.path IN (SELECT file_path FROM Top10Files)
        AND (LOWER(c.message) LIKE '%fix%' 
            OR LOWER(c.message) LIKE '%hotfix%' 
            OR LOWER(c.message) LIKE '%resolve%' 
            OR LOWER(c.message) LIKE '%solve%' 
            OR LOWER(c.message) LIKE '%refact%' 
            OR LOWER(c.message) LIKE '%refactor%' 
            OR LOWER(c.message) LIKE '%rewrite%' 
            OR LOWER(c.message) LIKE '%improve%' 
            OR LOWER(c.message) LIKE '%remake%' 
            OR LOWER(c.message) LIKE '%recode%')
    ORDER BY 
        f.path, c.date;
    """
    try:
        df = pd.read_sql_query(query, conn)
        # Converte a coluna de datas para o formato datetime
        df['date'] = pd.to_datetime(df['date'])
        return df
    except pd.io.sql.DatabaseError as e:
        log_error(f"Erro ao executar a query: {e}")
        return pd.DataFrame()

# Função para calcular o número de commits de erro entre refatorações


def calculate_errors_between_refactors(df):
    results = {}

    for path, group in df.groupby('path'):
        commits_refactor = group[group['tipo_commit'] == 'refatoracao']
        commits_error = group[group['tipo_commit'] == 'erro']

        if commits_refactor.empty:
            continue

        error_counts = []
        previous_refactor_date = None

        for _, refactor in commits_refactor.iterrows():
            refactor_date = refactor['date']

            if previous_refactor_date is not None:
                errors_in_interval = commits_error[
                    (commits_error['date'] > previous_refactor_date) &
                    (commits_error['date'] <= refactor_date)
                ]
                error_counts.append(len(errors_in_interval))

            previous_refactor_date = refactor_date

        results[path] = error_counts

    return results

# Função para gerar o gráfico


def plot_error_refactor_graph(errors_between_refactors):
    for path, error_counts in errors_between_refactors.items():
        # Vamos plotar as refatorações (pontuação) e os erros entre elas (barras)
        fig, ax = plt.subplots()

        # Posição dos commits de refatoração e exibição dos erros como barra
        # +1 para incluir o commit final
        refactor_commits = range(len(error_counts) + 1)
        # Adiciona zero no final para o último commit
        bar_heights = error_counts + [0]

        # Gráfico de barras (para erros)
        ax.bar(refactor_commits[:-1], bar_heights[:-1],
               color='red', label='Total de Erros')

        # Adicionar pontos para representar os commits de refatoração
        ax.scatter(refactor_commits, bar_heights, color='blue',
                   label='Commits de Refatoração')

        # Ajustar labels e título
        ax.set_xlabel('Intervalo de Refatoração')
        ax.set_ylabel('Total de Erros')
        ax.set_title(f'Commits de Erros entre Refatorações para {path}')
        ax.legend()

        # Exibir o gráfico
        # Remover labels dos commits
        plt.xticks(refactor_commits, labels=[''] * len(refactor_commits))
        plt.show()


def main():
    conn = connect_db()
    if conn is None:
        return

    # Executar a query e carregar os resultados
    df = get_data(conn)

    # Fechar a conexão
    conn.close()

    # Verificar se o DataFrame tem dados antes de gerar gráficos
    if df.empty:
        log_info("Nenhum dado encontrado para gerar gráficos.")
        return

    # Exibir o DataFrame com os resultados
    log_info(f"Dados retornados:\n{df}")

    errors_between_refactors = calculate_errors_between_refactors(df)

    plot_error_refactor_graph(errors_between_refactors)


if __name__ == "__main__":
    main()
