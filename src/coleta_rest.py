import time
import datetime
import requests
import pandas as pd

# ==============================================================================
# CONFIGURAÇÕES DA COLETA REST (OTIMIZADO)
# ==============================================================================
TOKEN = "COLOQUE_SEU_TOKEN_AQUI"
REPOSITORIOS_ALVO = 100
PRS_POR_REPO = 100
DELAY_API = 0.5  # Reduzido levemente, já que faremos menos chamadas no total

headers = {
    "Authorization": f"Bearer {TOKEN}",
    "Accept": "application/vnd.github.v3+json"
}

def fazer_requisicao_rest(url, params=None):
    inicio = time.time()
    response = requests.get(url, headers=headers, params=params)
    fim = time.time()
    
    tempo_execucao = fim - inicio
    tamanho_bytes = len(response.content) if response.content else 0
    
    return response, tempo_execucao, tamanho_bytes

def executar_coleta_rest():
    repositorios_validos = 0
    pagina_repo = 1
    
    dataset_final = []
    metricas_experimento = [] 

    print("=== INICIANDO COLETA REST (LAB 05 - SHORT-CIRCUIT) ===")
    
    while repositorios_validos < REPOSITORIOS_ALVO:
        print(f"Buscando repositórios (Página {pagina_repo})...")
        
        url_search = "https://api.github.com/search/repositories"
        params_search = {"q": "is:public", "sort": "stars", "order": "desc", "per_page": 100, "page": pagina_repo}
        
        resp_repos, tempo_req, tam_req = fazer_requisicao_rest(url_search, params_search)
        metricas_experimento.append({"tipo_req": "search_repos", "tempo_segundos": tempo_req, "tamanho_bytes": tam_req})
        
        if resp_repos.status_code != 200:
            print(f"Erro na API REST (Busca): {resp_repos.status_code}")
            break
            
        dados_repos = resp_repos.json().get("items", [])
        if not dados_repos:
            break

        for repo in dados_repos:
            if repositorios_validos >= REPOSITORIOS_ALVO:
                break
                
            nome_completo_repo = repo["full_name"]
            print(f"  [Analisando {repositorios_validos + 1}/{REPOSITORIOS_ALVO}] {nome_completo_repo}")
            
            url_prs = f"https://api.github.com/repos/{nome_completo_repo}/pulls"
            params_prs = {"state": "all", "sort": "created", "direction": "desc", "per_page": PRS_POR_REPO}
            
            resp_prs, tempo_prs, tam_prs = fazer_requisicao_rest(url_prs, params_prs)
            metricas_experimento.append({"tipo_req": "get_prs", "tempo_segundos": tempo_prs, "tamanho_bytes": tam_prs})
            
            if resp_prs.status_code != 200:
                time.sleep(DELAY_API)
                continue
                
            lista_prs = resp_prs.json()
            if not isinstance(lista_prs, list) or len(lista_prs) == 0:
                time.sleep(DELAY_API)
                continue
                
            repositorios_validos += 1
            
            for pr in lista_prs:
                estado = pr["state"]
                if estado not in ["closed", "merged"]:
                    continue
                
                # OTIMIZAÇÃO: Filtramos a data ANTES de pedir a requisição extra (N+1)
                data_criacao = pd.to_datetime(pr["created_at"])
                data_conclusao = pd.to_datetime(pr["merged_at"] if pr.get("merged_at") else pr["closed_at"])
                
                if pd.isnull(data_criacao) or pd.isnull(data_conclusao):
                    continue
                    
                duracao_revisao = data_conclusao - data_criacao
                uma_hora = datetime.timedelta(hours=1)
                
                # Se não durou 1 hora, ignora. Não gastamos requisição REST aqui!
                if duracao_revisao < uma_hora:
                    continue
                
                # Só faz a chamada cara (N+1) se o PR já passou no filtro de tempo
                url_reviews = f"https://api.github.com/repos/{nome_completo_repo}/pulls/{pr['number']}/reviews"
                resp_rev, tempo_rev, tam_rev = fazer_requisicao_rest(url_reviews, {"per_page": 1})
                metricas_experimento.append({"tipo_req": "get_reviews", "tempo_segundos": tempo_rev, "tamanho_bytes": tam_rev})
                
                total_revisoes = 0
                if resp_rev.status_code == 200:
                    total_revisoes = len(resp_rev.json()) 

                if total_revisoes < 1:
                    time.sleep(DELAY_API)
                    continue
                    
                # Se passou em tudo, salva no dataset
                dataset_final.append({
                    "repositorio": nome_completo_repo,
                    "total_stars_repo": repo["stargazers_count"],
                    "pr_numero": pr["number"],
                    "status_pr": "MERGED" if pr.get("merged_at") else "CLOSED",
                    "criado_em": pr["created_at"],
                    "concluido_em": pr["merged_at"] if pr.get("merged_at") else pr["closed_at"],
                    "duracao_revisao_horas": round(duracao_revisao.total_seconds() / 3600, 2),
                    "total_revisoes": total_revisoes
                })
                
                time.sleep(DELAY_API) 
            
        pagina_repo += 1
        time.sleep(DELAY_API)

    print("\n=== COLETA REST CONCLUÍDA ===")
    df_dataset = pd.DataFrame(dataset_final)
    df_dataset.to_csv("dataset_prs_rest.csv", index=False)
    df_metricas = pd.DataFrame(metricas_experimento)
    df_metricas.to_csv("metricas_desempenho_rest.csv", index=False)
    print(f"Dataset PRs gerado: {len(df_dataset)} linhas.")
    print(f"Métricas Lab 05 geradas: {len(df_metricas)} requisições monitoradas.")

if __name__ == "__main__":
    executar_coleta_rest()