import os
import sqlite3
import logging
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime

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


def connect_db():
    log_info("Conectando ao banco de dados...")
    db_path = os.path.join(repo_path, '..', 'kubernetes_logs.db')
    conn = sqlite3.connect(db_path)
    log_info("Conectado ao banco de dados.")
    return conn


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
        df['date'] = pd.to_datetime(df['date'])

        return df
    except pd.io.sql.DatabaseError as e:
        log_error(f"Erro ao executar a query: {e}")
        return pd.DataFrame()

# Função para gerar gráficos de densidade


def plot_density_graph(df):
    # Criar a pasta "graphs" se ela não existir
    output_dir = 'graphs'
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # Criar gráfico de densidade
    for path, group in df.groupby('path'):
        plt.figure(figsize=(10, 5))

        # Plotar densidade usando kdeplot e ajustando a largura da banda
        sns.kdeplot(data=group, x='date', hue='tipo_commit',
                    cut=0, fill=True, alpha=0.2)

        index = path.index('kubernetes')
        path = path[index:]

        # Ajustar labels e título
        plt.title(f'Densidade de Commits ao longo do tempo {path}')
        plt.xlabel('Tempo')
        plt.ylabel('Densidade')

        graph_filename = f"{output_dir}/{path.replace(os.sep, '_')}.png"

        plt.savefig(graph_filename)
        print(f"Gráfico salvo em: {graph_filename}")


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

    # Gerar gráfico de densidade
    plot_density_graph(df)


if __name__ == "__main__":
    main()
