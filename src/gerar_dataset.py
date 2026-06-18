import time
import datetime
import requests
import pandas as pd

# ==============================================================================
# CONFIGURAÇÕES DA COLETA
# ==============================================================================
# Substitua pelo seu Personal Access Token (PAT) clássico do GitHub
TOKEN = "SEU_PERSONAL_ACCESS_TOKEN_AQUI" 
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
# As três aspas (""") abrem e fecham a string de múltiplas linhas no Python
QUERY_GRAPHQL = """
query GetPopularRepos($cursor: String, $numPRs: Int!) {
  search(query: "is:public sort:stars-desc", type: REPOSITORY, first: 20, after: $cursor) {
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
# PIPELINE DE EXECUÇÃO E FILTRAGEM
# ==============================================================================
def executar_coleta():
    repositorios_validos_contados = 0
    cursor = None
    has_next_page = True
    
    dataset_final = []
    repos_processados_historico = []

    print("=== INICIANDO CONSTRUÇÃO DO DATASET ===")
    
    while has_next_page and repositorios_validos_contados < REPOSITORIOS_ALVO:
        print(f"Buscando lote de repositórios... (Válidos até agora: {repositorios_validos_contados}/{REPOSITORIOS_ALVO})")
        
        variables = {"cursor": cursor, "numPRs": PRS_POR_REPO}
        response = requests.post(URL_GRAPHQL, json={"query": QUERY_GRAPHQL, "variables": variables}, headers=headers)
        
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
            print(f"  [Processando {repositorios_validos_contados}/100] {nome_completo_repo}")
            
            prs_inseridos_deste_repo = 0
            
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
                        duracao_em_horas = duracao_revisao.total_seconds() / 3600
                        
                        dataset_final.append({
                            "repositorio": nome_completo_repo,
                            "total_stars_repo": repo["stargazerCount"],
                            "pr_numero": pr["number"],
                            "status_pr": pr["state"],
                            "criado_em": pr["createdAt"],
                            "concluido_em": pr["mergedAt"] if pr["mergedAt"] else pr["closedAt"],
                            "duracao_revisao_horas": round(duracao_em_horas, 2),
                            "total_revisoes": pr["reviews"]["totalCount"]
                        })
                        prs_inseridos_deste_repo += 1
            
            repos_processados_historico.append({
                "repositorio": nome_completo_repo,
                "prs_filtrados_inseridos": prs_inseridos_deste_repo
            })
            
            # Pausa para evitar rate limit
            time.sleep(DELAY_API)

    # ==============================================================================
    # EXPORTAÇÃO DOS ARQUIVOS CSV
    # ==============================================================================
    print("\n=== COLETA CONCLUÍDA ===")
    
    df_dataset = pd.DataFrame(dataset_final)
    df_dataset.to_csv("dataset_pull_requests.csv", index=False)
    print(f"Sucesso! Arquivo 'dataset_pull_requests.csv' gerado com {len(df_dataset)} linhas de PRs.")
    
    df_repos = pd.DataFrame(repos_processados_historico)
    df_repos.to_csv("relatorio_repositorios_analisados.csv", index=False)
    print("Arquivo de auditoria 'relatorio_repositorios_analisados.csv' gerado.")

if __name__ == "__main__":
    executar_coleta()