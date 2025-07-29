from pyproj import Transformer
import simplekml
import networkx as nx
from kml_utils import carregar_kml_raiz, extrair_geometrias_do_kml
from grafo_utils import construir_rede_em_grafo, inserir_caixas_na_rede_do_grafo
from exportador_kml import desenhar_grupo_no_mapa_kml
from algoritmo_genetico import algoritmo_genetico
from exportador_kml import desenhar_grupo_no_mapa_kml, exportar_componentes_desconectados_kml
import os

if __name__ == "__main__":
    # --- Configurações Iniciais ---
    arquivo_kml = "Estudo_complexo.kml"
    saida_kml = "agrupamento_genetico_estudo_2setor.kml"
    qtd_caixas_por_grupo = 6

    # --- Configurações do Algoritmo Genético ---
    n_pop = 100000
    n_ger = 200000

    ## NOVIDADE: Define o nome do arquivo de estado com base no arquivo KML
    nome_base_kml = os.path.splitext(os.path.basename(arquivo_kml))[0]
    arquivo_estado = f"{nome_base_kml}_estado.pkl"
    print(f"ℹ️  Arquivo de estado para esta execução: {arquivo_estado}")

    # --- Início do Processamento ---
    raiz = carregar_kml_raiz(caminho_do_arquivo=arquivo_kml)
    namespace_kml = {"kml": "http://www.opengis.net/kml/2.2"}

    linhas_geograficas, nomes_das_linhas, caixas_com_nome = extrair_geometrias_do_kml(raiz_kml=raiz,
                                                                                      namespace_kml=namespace_kml)
    print(f"DEBUG: {len(linhas_geograficas)} linhas elétricas encontradas. {len(caixas_com_nome)} caixas encontradas.")

    if not linhas_geograficas or not caixas_com_nome:
        print("Erro: verifique se o KML contém pastas 'linhas_eletricas' e 'Caixas' com geometria.")
        exit(1)

    conversor_para_grade = Transformer.from_crs("EPSG:4326", "EPSG:3857", always_xy=True)
    conversor_para_mapa = Transformer.from_crs("EPSG:3857", "EPSG:4326", always_xy=True)

    rede_grafo, segmentos_da_rede = construir_rede_em_grafo(
        linhas_geograficas=linhas_geograficas,
        conversor_de_coordenadas=conversor_para_grade
    )

    mapa_nomes_para_coordenadas = inserir_caixas_na_rede_do_grafo(
        rede_grafo=rede_grafo,
        segmentos_da_rede=segmentos_da_rede,
        lista_de_caixas_com_nome=caixas_com_nome,
        conversor_de_coordenadas=conversor_para_grade,
        tolerancia_conexao_proxima=2.0,
        raio_maximo_busca=5.0
    )

    # ## OTIMIZAÇÃO: CÓDIGO DE DIAGNÓSTICO DO GRAFO (ATUALIZADO) ##
    # #############################################################
    print("\n--- Verificando a Conectividade do Grafo ---")
    if nx.is_connected(rede_grafo):
        print("✅ O grafo da rede está totalmente conectado.")
    else:
        num_componentes = nx.number_connected_components(rede_grafo)
        print(f"❌ ATENÇÃO: O grafo da rede NÃO está conectado.")
        print(f"   Ele está dividido em {num_componentes} 'ilhas' (componentes) separadas.")

        # Gera o KML de diagnóstico
        caminho_diagnostico = "diagnostico_componentes.kml"
        exportar_componentes_desconectados_kml(
            rede_grafo=rede_grafo,
            conversor_de_coordenadas_para_mapa=conversor_para_mapa,
            caminho_arquivo_saida=caminho_diagnostico
        )

        print("\nO programa será encerrado. Corrija a conectividade da rede antes de continuar.")
        print("Dica: Aumente o parâmetro 'tolerancia_conexao_proxima' na função 'inserir_caixas_na_rede_do_grafo'.")
        exit()  # Encerra o script
    # #############################################################

    print("\nPré-calculando matriz de distâncias entre todas as caixas. Aguarde...")

    print("\nPré-calculando matriz de distâncias entre todas as caixas. Aguarde...")
    ## OTIMIZAÇÃO: Pré-cálculo de todas as distâncias entre as caixas.
    # Este passo, embora possa demorar um pouco, é executado APENAS UMA VEZ.
    # Ele economiza milhões de cálculos dentro do algoritmo genético.
    print("\nPré-calculando matriz de distâncias entre todas as caixas. Aguarde...")
    distancias_precalculadas = {}
    # Obtém a lista de nós do grafo que correspondem a caixas
    nos_das_caixas = list(mapa_nomes_para_coordenadas.values())

    # Calcula o caminho mais curto de cada caixa para todas as outras
    # O resultado é um dicionário no formato: {nome_caixa_origem: {nome_caixa_destino: distancia}}
    for no_origem in nos_das_caixas:
        # Encontra o nome da caixa correspondente ao nó de origem
        nome_origem = next((nome for nome, coord in mapa_nomes_para_coordenadas.items() if coord == no_origem), None)
        if nome_origem:
            distancias_precalculadas[nome_origem] = {}
            # Calcula o caminho mais curto do nó de origem para todos os outros nós das caixas
            comprimentos = nx.single_source_dijkstra_path_length(rede_grafo, source=no_origem, weight='weight')

            for no_destino in nos_das_caixas:
                if no_destino in comprimentos:
                    # Encontra o nome da caixa correspondente ao nó de destino
                    nome_destino = next(
                        (nome for nome, coord in mapa_nomes_para_coordenadas.items() if coord == no_destino), None)
                    if nome_destino:
                        distancias_precalculadas[nome_origem][nome_destino] = comprimentos[no_destino]
    print("Matriz de distâncias calculada com sucesso!")

    # A chamada da função agora usa o dicionário de distâncias pré-calculadas.
    grupos_calculados = algoritmo_genetico(
        mapa_caixa_no=mapa_nomes_para_coordenadas,
        distancias_precalculadas=distancias_precalculadas,  # Novo argumento
        qtd_caixas=qtd_caixas_por_grupo,
        n_pop=n_pop,
        n_ger=n_ger,

    # --- NOVOS PARÂMETROS ---
    # Quantas gerações esperar sem melhora antes de aumentar a mutação
    paciencia_adaptacao = 30,
        # Quantas gerações esperar sem melhora antes de parar tudo
    paciencia_parada = 60,
        # Quantos indivíduos "campeões" devem sobreviver a cada geração
    elitismo_tamanho = 2,
        # Taxa de mutação normal
    taxa_mutacao_inicial = 0.02,
        # Taxa de mutação alta para quando o algoritmo estagnar
    taxa_mutacao_adaptativa = 0.20,

    ## NOVIDADE: Passa o caminho do arquivo de estado para a função
    arquivo_estado = arquivo_estado
    )

    # --- Processamento Final com Prevenção de Sobreposição por Roteamento ---
    # (O restante do código permanece o mesmo)
    grupos_finais_para_kml = []
    if grupos_calculados:
        print("\nProcessando solução final para KML com prevenção de sobreposição...")

        grafo_para_roteamento = rede_grafo.copy()

        for i, grupo in enumerate(grupos_calculados):
            hub_nome = grupo.get("hub")
            membros_grupo = grupo.get("grupo", [])
            conexoes_principais_grupo = set()

            if not hub_nome or not membros_grupo:
                print(f"  - AVISO: Grupo {i + 1} inválido (sem hub ou membros). Ignorando.")
                continue

            try:
                hub_node = mapa_nomes_para_coordenadas[hub_nome]

                for nome_caixa in membros_grupo:
                    if nome_caixa == hub_nome:
                        continue
                    caixa_node = mapa_nomes_para_coordenadas[nome_caixa]
                    caminho = nx.shortest_path(grafo_para_roteamento, source=hub_node, target=caixa_node,
                                               weight='weight')
                    for j in range(len(caminho) - 1):
                        u, v = caminho[j], caminho[j + 1]
                        conexoes_principais_grupo.add(tuple(sorted((u, v))))

                print(
                    f"  - Grupo {i + 1} (Hub: {hub_nome}): {len(membros_grupo)} caixas. Rota com {len(conexoes_principais_grupo)} segmentos de cabo."
                )

                for u, v in conexoes_principais_grupo:
                    if grafo_para_roteamento.has_edge(u, v):
                        grafo_para_roteamento.remove_edge(u, v)

            except (nx.NetworkXNoPath, KeyError) as e:
                print(
                    f"  - ERRO: Grupo {i + 1} (Hub: {hub_nome}) não pôde ser roteado. Causa: {e}. O grupo será desenhado sem cabos."
                )
                conexoes_principais_grupo = set()

            grupos_finais_para_kml.append({
                "nome_hub": hub_nome,
                "grupo_final": membros_grupo,
                "conexoes_principais": list(conexoes_principais_grupo),
                "conexoes_secundarias": []
            })
    else:
        print("Algoritmo genético não retornou nenhuma solução.")

    # --- Verificação Final de Sobreposição ---
    arestas_utilizadas_verificacao = set()
    sobreposicoes = False
    for grupo in grupos_finais_para_kml:
        for u, v in grupo["conexoes_principais"]:
            aresta = frozenset([u, v])
            if aresta in arestas_utilizadas_verificacao:
                print(f"Sobreposição detectada na aresta {aresta}!")
                sobreposicoes = True
            arestas_utilizadas_verificacao.add(aresta)

    if not sobreposicoes:
        print("Nenhuma sobreposição detectada nas rotas.")

    # --- Desenho do KML ---
    documento_kml_final = simplekml.Kml()
    for i, dados_grupo_kml in enumerate(grupos_finais_para_kml):
        nome_pasta = f"Grupo {i + 1} - {len(dados_grupo_kml['grupo_final'])} caixas"

        desenhar_grupo_no_mapa_kml(
            cabo_primario=dados_grupo_kml["conexoes_principais"],
            cabo_secundario=dados_grupo_kml["conexoes_secundarias"],
            mapa_nomes_para_coordenadas=mapa_nomes_para_coordenadas,
            nome_da_caixa_hub=dados_grupo_kml["nome_hub"],
            lista_de_caixas_do_grupo=dados_grupo_kml["grupo_final"],
            conversor_de_coordenadas_para_mapa=conversor_para_mapa,
            documento_kml_existente=documento_kml_final,
            nome_da_pasta_no_mapa=nome_pasta
        )

    documento_kml_final.save(saida_kml)
    print(f"\nKML com rotas exclusivas salvo em: {saida_kml}")