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

# Gera um gráfico de barras a partir dos dados.


def generate_bar_graph_per_file(df):
    sns.set_theme(style="whitegrid")
    unique_files = df['path'].unique()

    for file_path in unique_files:
        # Filtrar o DataFrame por arquivo
        df_file = df[df['path'] == file_path]

        # Criar gráfico de barras para cada arquivo, ordenando por data
        plt.figure(figsize=(10, 7))
        sns.countplot(data=df_file, x='date',
                      hue='tipo_commit', palette='viridis')

        # Adicionar rótulos e título
        plt.title(f'Commits por Tipo no Arquivo: {file_path}')
        plt.xlabel('Data')
        plt.ylabel('Número de Commits')

        # Rotacionar rótulos do eixo X para melhor visualização
        plt.xticks(rotation=45)

        # Ajustar layout e exibir o gráfico
        plt.tight_layout()
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

    # Gerar gráfico para cada arquivo
    generate_bar_graph_per_file(df)


if __name__ == "__main__":
    main()
