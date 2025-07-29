from typing import List, Tuple, Dict
from shapely.geometry import LineString, Point
from shapely.ops import transform as shapely_transform
import networkx as nx
from pyproj import Transformer


def construir_rede_em_grafo(
        linhas_geograficas: List[LineString],
        conversor_de_coordenadas: Transformer
) -> Tuple[nx.Graph, List[Dict]]:
    """
    Constrói uma representação de grafo a partir de linhas geográficas.

    Args:
        linhas_geograficas: Uma lista de objetos LineString.
        conversor_de_coordenadas: Um objeto Transformer do pyproj para projeção.

    Returns:
        Uma tupla contendo o grafo NetworkX e uma lista de todos os segmentos de linha.
    """
    rede_grafo = nx.Graph()
    segmentos_da_rede: List[Dict] = []

    for linha in linhas_geograficas:
        # Projeta a linha geográfica para um sistema de coordenadas cartesiano (em metros)
        linha_projetada = shapely_transform(conversor_de_coordenadas.transform, linha)
        coordenadas = list(linha_projetada.coords)

        # Itera sobre cada par de coordenadas para formar um segmento
        for i in range(len(coordenadas) - 1):
            ponto_a = coordenadas[i]
            ponto_b = coordenadas[i + 1]
            distancia = ((ponto_a[0] - ponto_b[0]) ** 2 + (ponto_a[1] - ponto_b[1]) ** 2) ** 0.5

            # Adiciona os pontos (nós) e o caminho (aresta) ao grafo
            rede_grafo.add_node(ponto_a)
            rede_grafo.add_node(ponto_b)
            if rede_grafo.has_edge(ponto_a, ponto_b):
                # Se a aresta já existe, mantém apenas o menor peso (distância)
                if distancia < rede_grafo[ponto_a][ponto_b]['weight']:
                    rede_grafo[ponto_a][ponto_b]['weight'] = distancia
            else:
                rede_grafo.add_edge(ponto_a, ponto_b, weight=distancia)

            # Guarda o segmento para uso futuro
            segmentos_da_rede.append({'a': ponto_a, 'b': ponto_b, 'geom': LineString([ponto_a, ponto_b])})

    return rede_grafo, segmentos_da_rede


def inserir_caixas_na_rede_do_grafo(
        rede_grafo: nx.Graph,
        segmentos_da_rede: List[Dict],
        lista_de_caixas_com_nome: List[Tuple[Point, str]],
        conversor_de_coordenadas: Transformer,
        tolerancia_conexao_proxima: float = 2.0,
        raio_maximo_busca: float = 5.0
) -> Dict[str, Tuple[float, float]]:
    """
    Insere as caixas no grafo, projetando-as no segmento de linha mais próximo,
    desde que a distância seja menor que o 'raio_maximo_busca'.
    """
    mapa_nomes_para_coordenadas: Dict[str, Tuple[float, float]] = {}
    epsilon = 1e-6  # Uma tolerância mínima para comparar pontos flutuantes

    for ponto_caixa, nome_caixa in lista_de_caixas_com_nome:
        # Projeta o ponto geográfico da caixa para o sistema de coordenadas do grafo
        ponto_caixa_projetado = shapely_transform(conversor_de_coordenadas.transform, ponto_caixa)

        # Encontra o segmento de linha mais próximo da caixa
        distancia_minima = float('inf')
        segmento_mais_proximo = None
        for segmento in segmentos_da_rede:
            dist = segmento['geom'].distance(ponto_caixa_projetado)
            if dist < distancia_minima:
                distancia_minima = dist
                segmento_mais_proximo = segmento

        # Se a caixa estiver muito longe da rede, ignora-a.
        if distancia_minima > raio_maximo_busca or segmento_mais_proximo is None:
            print(f"Caixa '{nome_caixa}' está a {distancia_minima:.2f}m da linha mais próxima. Ignorada.")
            continue

        # Projeta o ponto da caixa sobre o segmento de linha mais próximo
        ponto_na_linha = segmento_mais_proximo['geom'].interpolate(
            segmento_mais_proximo['geom'].project(ponto_caixa_projetado)
        )
        x_proj, y_proj = ponto_na_linha.x, ponto_na_linha.y
        coordenada_da_caixa_na_rede = (x_proj, y_proj)

        # Verifica se já existe um nó no grafo muito perto desta posição
        no_existente_proximo = None
        for no_existente in rede_grafo.nodes():
            if ((no_existente[0] - x_proj) ** 2 + (no_existente[1] - y_proj) ** 2) ** 0.5 < epsilon:
                no_existente_proximo = no_existente
                break

        if no_existente_proximo is not None:
            mapa_nomes_para_coordenadas[nome_caixa] = no_existente_proximo
            continue

        # Se não houver um nó próximo, "quebra" o segmento e insere a caixa
        ponto_a = segmento_mais_proximo['a']
        ponto_b = segmento_mais_proximo['b']

        if rede_grafo.has_edge(ponto_a, ponto_b):
            rede_grafo.remove_edge(ponto_a, ponto_b)
        segmentos_da_rede.remove(segmento_mais_proximo)

        # Adiciona o novo nó da caixa e as duas novas arestas que o conectam
        rede_grafo.add_node(coordenada_da_caixa_na_rede)
        dist_a_caixa = ((ponto_a[0] - x_proj) ** 2 + (ponto_a[1] - y_proj) ** 2) ** 0.5
        dist_caixa_b = ((x_proj - ponto_b[0]) ** 2 + (y_proj - ponto_b[1]) ** 2) ** 0.5
        rede_grafo.add_edge(ponto_a, coordenada_da_caixa_na_rede, weight=dist_a_caixa)
        rede_grafo.add_edge(coordenada_da_caixa_na_rede, ponto_b, weight=dist_caixa_b)

        # Adiciona os dois novos segmentos à lista
        segmentos_da_rede.append({'a': ponto_a, 'b': coordenada_da_caixa_na_rede,
                                  'geom': LineString([ponto_a, coordenada_da_caixa_na_rede])})
        segmentos_da_rede.append({'a': coordenada_da_caixa_na_rede, 'b': ponto_b,
                                  'geom': LineString([coordenada_da_caixa_na_rede, ponto_b])})

        mapa_nomes_para_coordenadas[nome_caixa] = coordenada_da_caixa_na_rede

    # Opcional: Conecta nós que estão muito próximos um do outro
    todos_nos = list(rede_grafo.nodes())
    num_nos = len(todos_nos)
    for i in range(num_nos):
        no1_x, no1_y = todos_nos[i]
        for j in range(i + 1, num_nos):
            no2_x, no2_y = todos_nos[j]
            distancia_entre_nos = ((no1_x - no2_x) ** 2 + (no1_y - no2_y) ** 2) ** 0.5
            if distancia_entre_nos < tolerancia_conexao_proxima and not rede_grafo.has_edge(todos_nos[i], todos_nos[j]):
                rede_grafo.add_edge(todos_nos[i], todos_nos[j], weight=distancia_entre_nos)

    return mapa_nomes_para_coordenadas