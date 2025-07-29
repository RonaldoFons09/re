import random
from typing import List, Dict, Any, Tuple
import networkx as nx
from functools import partial
from multiprocessing import Pool
import pickle  # NOVIDADE: Importa a biblioteca para salvar/carregar estado
import os  # NOVIDADE: Importa para verificar se o arquivo existe


# ... (as funções _criar_individuo, _calcular_aptidao, etc. continuam as mesmas) ...
def _criar_individuo(lista_de_caixas: List[str]) -> List[str]:
    individuo = list(lista_de_caixas)
    random.shuffle(individuo)
    return individuo


def _calcular_aptidao(individuo: List[str], distancias: Dict[str, Dict[str, float]], qtd_caixas: int) -> float:
    distancia_total = 0.0
    for i in range(0, len(individuo), qtd_caixas):
        grupo_nomes = individuo[i:i + qtd_caixas]
        if not grupo_nomes:
            continue
        hub_nome = grupo_nomes[0]
        if hub_nome not in distancias:
            distancia_total += 1e9 * len(grupo_nomes)
            continue
        for nome_caixa in grupo_nomes[1:]:
            distancia = distancias[hub_nome].get(nome_caixa, 1e9)
            distancia_total += distancia
    return distancia_total


def _calcular_aptidao_wrapper(individuo: List[str], distancias: Dict[str, Dict[str, float]], qtd_caixas: int) -> float:
    return _calcular_aptidao(individuo, distancias, qtd_caixas)


def _selecao_torneio(populacao: List[List[str]], aptidoes: List[float], k: int = 3) -> List[str]:
    indices_torneio = random.sample(range(len(populacao)), k)
    melhor_indice_no_torneio = min(indices_torneio, key=lambda i: aptidoes[i])
    return populacao[melhor_indice_no_torneio]


def _cruzamento(pai1: List[str], pai2: List[str], qtd_caixas: int) -> List[str]:
    filho = [None] * len(pai1)
    ponto_inicio = random.randrange(0, len(pai1), qtd_caixas)
    ponto_fim = ponto_inicio + qtd_caixas
    segmento_pai1 = pai1[ponto_inicio:ponto_fim]
    filho[ponto_inicio:ponto_fim] = segmento_pai1
    ponteiro_pai2 = 0
    for i in range(len(filho)):
        if filho[i] is None:
            while pai2[ponteiro_pai2] in segmento_pai1:
                ponteiro_pai2 += 1
            filho[i] = pai2[ponteiro_pai2]
            ponteiro_pai2 += 1
    return filho


def _mutacao(individuo: List[str], taxa_mutacao: float = 0.05) -> List[str]:
    if random.random() < taxa_mutacao:
        idx1, idx2 = random.sample(range(len(individuo)), 2)
        individuo[idx1], individuo[idx2] = individuo[idx2], individuo[idx1]
    return individuo


def algoritmo_genetico(
        mapa_caixa_no: Dict[str, Tuple],
        distancias_precalculadas: Dict[str, Dict[str, float]],
        qtd_caixas: int,
        n_pop: int,
        n_ger: int,
        taxa_mutacao_inicial: float = 0.02,
        taxa_mutacao_adaptativa: float = 0.20,
        paciencia_adaptacao: int = 30,
        paciencia_parada: int = 50,
        elitismo_tamanho: int = 2,
        ## NOVIDADE: Parâmetro com o caminho do arquivo de estado
        arquivo_estado: str = None
) -> List[Dict[str, Any]]:
    print("\n--- Iniciando Algoritmo Genético Avançado ---")
    lista_de_nomes_caixas = list(mapa_caixa_no.keys())

    ## NOVIDADE: Lógica para carregar o estado anterior
    ger_inicial = 0
    populacao = []
    melhor_individuo_global = None
    melhor_aptidao_global = float('inf')
    taxa_mutacao_atual = taxa_mutacao_inicial
    geracoes_sem_melhora = 0

    if arquivo_estado and os.path.exists(arquivo_estado):
        try:
            with open(arquivo_estado, 'rb') as f:
                estado = pickle.load(f)

            # Restaura as variáveis salvas
            populacao = estado['populacao']
            melhor_individuo_global = estado['melhor_individuo_global']
            melhor_aptidao_global = estado['melhor_aptidao_global']
            ger_inicial = estado['ultima_geracao'] + 1
            geracoes_sem_melhora = estado['geracoes_sem_melhora']
            taxa_mutacao_atual = estado['taxa_mutacao_atual']

            print(f"✅ Progresso encontrado! Retomando da geração {ger_inicial}.")
        except Exception as e:
            print(
                f"⚠️ Aviso: Não foi possível carregar o arquivo de estado '{arquivo_estado}'. Começando do zero. Erro: {e}")
            ger_inicial = 0  # Garante que começará do zero em caso de erro

    # Se a população não foi carregada, cria uma nova
    if not populacao:
        print("Nenhum progresso encontrado ou falha no carregamento. Iniciando do zero.")
        populacao = [_criar_individuo(lista_de_nomes_caixas) for _ in range(n_pop)]

    if ger_inicial >= n_ger:
        print("O treinamento salvo já completou ou excedeu o número de gerações alvo.")

    calculador_de_aptidao_parcial = partial(_calcular_aptidao_wrapper, distancias=distancias_precalculadas,
                                            qtd_caixas=qtd_caixas)

    with Pool() as pool:
        # O loop agora começa da 'ger_inicial'
        for ger in range(ger_inicial, n_ger):
            # (A lógica de avaliação, elitismo, adaptação e parada continua a mesma)
            aptidoes = pool.map(calculador_de_aptidao_parcial, populacao)

            melhor_aptidao_da_geracao = min(aptidoes)

            if melhor_aptidao_da_geracao < melhor_aptidao_global:
                melhor_aptidao_global = melhor_aptidao_da_geracao
                melhor_individuo_global = populacao[aptidoes.index(melhor_aptidao_da_geracao)]
                geracoes_sem_melhora = 0
                taxa_mutacao_atual = taxa_mutacao_inicial
                print(f"Geração {ger + 1}/{n_ger} | 🏆 Nova Melhor Aptidão: {melhor_aptidao_global:.2f}m")
            else:
                geracoes_sem_melhora += 1
                if (ger + 1) % 10 == 0:
                    print(
                        f"Geração {ger + 1}/{n_ger} | Aptidão Estagnada: {melhor_aptidao_global:.2f}m (sem melhora há {geracoes_sem_melhora} gerações)")

            if geracoes_sem_melhora >= paciencia_parada:
                print(
                    f"\n⏹️ Parada Antecipada na geração {ger + 1}. A solução não melhora há {paciencia_parada} gerações.")
                break

            if geracoes_sem_melhora == paciencia_adaptacao:
                taxa_mutacao_atual = taxa_mutacao_adaptativa
                print(
                    f"⚠️  Estagnação detectada! Aumentando a taxa de mutação para {taxa_mutacao_atual * 100:.0f}% por um tempo.")

            nova_populacao = []
            populacao_ordenada = [x for _, x in sorted(zip(aptidoes, populacao), key=lambda pair: pair[0])]
            elite = populacao_ordenada[:elitismo_tamanho]
            nova_populacao.extend(elite)

            for _ in range(elitismo_tamanho, n_pop):
                pai1 = _selecao_torneio(populacao, aptidoes)
                pai2 = _selecao_torneio(populacao, aptidoes)
                filho = _cruzamento(pai1, pai2, qtd_caixas)
                filho_mutado = _mutacao(filho, taxa_mutacao_atual)
                nova_populacao.append(filho_mutado)

            populacao = nova_populacao

            ## NOVIDADE: Lógica para salvar o estado periodicamente
            if arquivo_estado and (ger + 1) % 2 == 0:  # Salva a cada 2 gerações
                estado_atual = {
                    'populacao': populacao,
                    'melhor_individuo_global': melhor_individuo_global,
                    'melhor_aptidao_global': melhor_aptidao_global,
                    'ultima_geracao': ger,
                    'geracoes_sem_melhora': geracoes_sem_melhora,
                    'taxa_mutacao_atual': taxa_mutacao_atual,
                }
                with open(arquivo_estado, 'wb') as f:
                    pickle.dump(estado_atual, f)
                # print(f"💾 Progresso salvo na geração {ger + 1}.") # descomente se quiser uma mensagem a cada salvamento

    # (A lógica de decodificação do resultado final permanece a mesma)
    print("--- Algoritmo Genético Finalizado ---")
    grupos_finais = []
    if melhor_individuo_global:
        for i in range(0, len(melhor_individuo_global), qtd_caixas):
            nomes_grupo = melhor_individuo_global[i:i + qtd_caixas]
            if nomes_grupo:
                grupos_finais.append({
                    "hub": nomes_grupo[0],
                    "grupo": nomes_grupo
                })

    return grupos_finais