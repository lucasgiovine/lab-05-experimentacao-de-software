import time
import datetime
import requests
import pandas as pd

# ==============================================================================
# CONFIGURAÇÕES DA COLETA GRAPHQL
# ==============================================================================
TOKEN = "COLOQUE_SEU_TOKEN_AQUI"
REPOSITORIOS_ALVO = 100
PRS_POR_REPO = 100  # Quantidade de PRs a inspecionar por repositório (máx: 100)
DELAY_API = 0.6     # Tempo de espera para evitar o bloqueio (rate limit) do GitHub

URL_GRAPHQL = "https://api.github.com/graphql"
headers = {
    "Authorization": f"Bearer {TOKEN}",
    "Content-Type": "application/json"
}

# ==============================================================================
# QUERY GRAPHQL COM PAGINAÇÃO
# ==============================================================================
QUERY_GRAPHQL = """
query GetPopularRepos($cursor: String, $numPRs: Int!) {
  search(query: "is:public sort:stars-desc", type: REPOSITORY, first: 5, after: $cursor) {
    pageInfo {
      endCursor
      hasNextPage
    }
    nodes {
      ... on Repository {
        name
        owner {
          login
        }
        stargazerCount
        totalPRsCount: pullRequests(states: [MERGED, CLOSED]) {
          totalCount
        }
        pullRequests(states: [MERGED, CLOSED], first: $numPRs, orderBy: {field: CREATED_AT, direction: DESC}) {
          nodes {
            number
            state
            createdAt
            closedAt
            mergedAt
            reviews {
              totalCount
            }
          }
        }
      }
    }
  }
}
"""

# ==============================================================================
# PIPELINE DE EXECUÇÃO E FILTRAGEM (LAB 05)
# ==============================================================================
def executar_coleta_graphql():
    repositorios_validos_contados = 0
    cursor = None
    has_next_page = True
    
    dataset_final = []
    metricas_experimento = [] # Armazena dados de RQ1 (Tempo) e RQ2 (Tamanho)

    print("=== INICIANDO COLETA GRAPHQL (LAB 05) ===")
    
    while has_next_page and repositorios_validos_contados < REPOSITORIOS_ALVO:
        print(f"Buscando lote de repositórios... (Válidos até agora: {repositorios_validos_contados}/{REPOSITORIOS_ALVO})")
        
        variables = {"cursor": cursor, "numPRs": PRS_POR_REPO}
        
        # INÍCIO DO CRONÔMETRO E COLETA DE MÉTRICAS DA REQUISIÇÃO
        inicio_req = time.time()
        response = requests.post(URL_GRAPHQL, json={"query": QUERY_GRAPHQL, "variables": variables}, headers=headers)
        fim_req = time.time()
        
        tempo_execucao = fim_req - inicio_req
        tamanho_bytes = len(response.content) if response.content else 0
        
        metricas_experimento.append({
            "tipo_req": "graphql_query_completa", 
            "tempo_segundos": tempo_execucao, 
            "tamanho_bytes": tamanho_bytes
        })
        # FIM DA COLETA DE MÉTRICAS
        
        if response.status_code != 200:
            print(f"Erro na API do GitHub: {response.status_code}")
            break
            
        dados = response.json()
        
        if "errors" in dados:
            print("Erro na estrutura da query GraphQL:", dados["errors"])
            break
            
        search_data = dados["data"]["search"]
        nodes = search_data["nodes"]
        
        # Atualiza cursores para a próxima página de resultados
        cursor = search_data["pageInfo"]["endCursor"]
        has_next_page = search_data["pageInfo"]["hasNextPage"]
        
        for repo in nodes:
            if not repo or repositorios_validos_contados >= REPOSITORIOS_ALVO:
                break
                
            nome_completo_repo = f"{repo['owner']['login']}/{repo['name']}"
            total_prs_repo = repo["totalPRsCount"]["totalCount"]
            
            # Filtro 1: Mínimo de 100 PRs totais no repositório
            if total_prs_repo < 100:
                continue
                
            repositorios_validos_contados += 1
            print(f"  [Processando {repositorios_validos_contados}/{REPOSITORIOS_ALVO}] {nome_completo_repo}")
            
            for pr in repo["pullRequests"]["nodes"]:
                # Filtro 2: Pelo menos 1 revisão de código
                if pr["reviews"]["totalCount"] < 1:
                    continue  
                    
                data_criacao = pd.to_datetime(pr["createdAt"])
                data_conclusao = pd.to_datetime(pr["mergedAt"] if pr["mergedAt"] else pr["closedAt"])
                
                if pd.notnull(data_criacao) and pd.notnull(data_conclusao):
                    duracao_revisao = data_conclusao - data_criacao
                    uma_hora = datetime.timedelta(hours=1)
                    
                    # Filtro 3: Tempo de revisão maior que 1 hora
                    if duracao_revisao >= uma_hora:
                        dataset_final.append({
                            "repositorio": nome_completo_repo,
                            "total_stars_repo": repo["stargazerCount"],
                            "pr_numero": pr["number"],
                            "status_pr": pr["state"],
                            "criado_em": pr["createdAt"],
                            "concluido_em": pr["mergedAt"] if pr["mergedAt"] else pr["closedAt"],
                            "duracao_revisao_horas": round(duracao_revisao.total_seconds() / 3600, 2),
                            "total_revisoes": pr["reviews"]["totalCount"]
                        })
            
            # Pausa para evitar rate limit
            time.sleep(DELAY_API)

    # ==============================================================================
    # EXPORTAÇÃO DOS ARQUIVOS CSV
    # ==============================================================================
    print("\n=== COLETA GRAPHQL CONCLUÍDA ===")
    
    # Exporta o Dataset de Negócio (PRs)
    df_dataset = pd.DataFrame(dataset_final)
    df_dataset.to_csv("dataset_prs_graphql.csv", index=False)
    
    # Exporta o Dataset de Métricas (RQ1 e RQ2)
    df_metricas = pd.DataFrame(metricas_experimento)
    df_metricas.to_csv("metricas_desempenho_graphql.csv", index=False)
    
    print(f"Dataset PRs gerado: {len(df_dataset)} linhas.")
    print(f"Métricas Lab 05 geradas: {len(df_metricas)} requisições monitoradas.")

if __name__ == "__main__":
    executar_coleta_graphql()