from typing import List, Tuple, Dict
from pyproj import Transformer
import simplekml
import networkx as nx
from shapely.geometry import LineString, MultiLineString
from shapely.ops import linemerge


def desenhar_grupo_no_mapa_kml(
        cabo_primario: List[Tuple],
        cabo_secundario: List[Tuple],
        mapa_nomes_para_coordenadas: Dict,
        nome_da_caixa_hub: str,
        lista_de_caixas_do_grupo: List[str],
        conversor_de_coordenadas_para_mapa: Transformer,
        arquivo_de_saida_kml: str = None,
        documento_kml_existente: simplekml.Kml = None,
        nome_da_pasta_no_mapa: str = "Grupo"
):
    """
    Desenha um grupo de rede (caixas e cabos) em um documento KML para visualização em mapas.

    Esta função pega uma solução de rede calculada e a representa visualmente,
    criando pastas, pontos e linhas com estilos apropriados no KML.
    """

    # Se nenhum documento KML existente for fornecido, cria um novo.
    if documento_kml_existente is None:
        documento_kml_existente = simplekml.Kml()

    # Cria a estrutura de pastas dentro do KML para organizar os elementos.
    pasta_grupo = documento_kml_existente.newfolder(name=nome_da_pasta_no_mapa)
    pasta_rede_acesso = pasta_grupo.newfolder(name="RA (Cabos)")
    pasta_caixas = pasta_grupo.newfolder(name="Caixas (Pontos)")

    # Tenta obter a coordenada da caixa central para evitar erros.
    try:
        no_hub = mapa_nomes_para_coordenadas[nome_da_caixa_hub]
    except KeyError:
        print(f"Erro: O nome da caixa central '{nome_da_caixa_hub}' não foi encontrado no mapa de coordenadas.")
        return

    # 1. Desenha as conexões principais (espinha dorsal da rede)
    grafo_cabo_primario = nx.Graph()
    for ponto_inicio, ponto_fim in cabo_primario:
        try:
            # Converte as coordenadas do sistema interno para Latitude/Longitude
            lonlat_inicio = conversor_de_coordenadas_para_mapa.transform(*ponto_inicio)
            lonlat_fim = conversor_de_coordenadas_para_mapa.transform(*ponto_fim)
            grafo_cabo_primario.add_edge(lonlat_inicio, lonlat_fim)
        except Exception as e:
            print(f"Erro ao transformar coordenadas da conexão principal ({ponto_inicio}, {ponto_fim}): {e}")

    # Otimiza o desenho unindo segmentos de linha contínuos
    for componente_conectado in nx.connected_components(grafo_cabo_primario):
        subgrafo = grafo_cabo_primario.subgraph(componente_conectado)
        segmentos_para_unir = [LineString([p1, p2]) for p1, p2 in subgrafo.edges()]
        if segmentos_para_unir:
            geometria_unida = linemerge(segmentos_para_unir)
            # Desenha a geometria unida no KML com o estilo apropriado
            if isinstance(geometria_unida, MultiLineString):
                for linha in geometria_unida.geoms:
                    linha_kml = pasta_rede_acesso.newlinestring()
                    linha_kml.coords = list(linha.coords)
                    linha_kml.style.linestyle.color = simplekml.Color.red
                    linha_kml.style.linestyle.width = 3
            else:
                linha_kml = pasta_rede_acesso.newlinestring()
                linha_kml.coords = list(geometria_unida.coords)
                linha_kml.style.linestyle.color = simplekml.Color.red
                linha_kml.style.linestyle.width = 3

    # 2. Desenha as conexões secundárias (rede de distribuição)
    # A lógica é idêntica à das conexões principais, apenas com estilo diferente.
    grafo_cabo_secundario = nx.Graph()
    for ponto_inicio, ponto_fim in cabo_secundario:
        try:
            lonlat_inicio = conversor_de_coordenadas_para_mapa.transform(*ponto_inicio)
            lonlat_fim = conversor_de_coordenadas_para_mapa.transform(*ponto_fim)
            grafo_cabo_secundario.add_edge(lonlat_inicio, lonlat_fim)
        except Exception as e:
            print(f"Erro ao transformar coordenadas da conexão secundária ({ponto_inicio}, {ponto_fim}): {e}")

    for componente_conectado in nx.connected_components(grafo_cabo_secundario):
        subgrafo = grafo_cabo_secundario.subgraph(componente_conectado)
        segmentos_para_unir = [LineString([p1, p2]) for p1, p2 in subgrafo.edges()]
        if segmentos_para_unir:
            geometria_unida = linemerge(segmentos_para_unir)
            if isinstance(geometria_unida, MultiLineString):
                for linha in geometria_unida.geoms:
                    linha_kml = pasta_rede_acesso.newlinestring()
                    linha_kml.coords = list(linha.coords)
                    linha_kml.style.linestyle.color = simplekml.Color.blue
                    linha_kml.style.linestyle.width = 2
            else:
                linha_kml = pasta_rede_acesso.newlinestring()
                linha_kml.coords = list(geometria_unida.coords)
                linha_kml.style.linestyle.color = simplekml.Color.blue
                linha_kml.style.linestyle.width = 2

    # 3. Desenha as caixas (pontos no mapa)
    for nome_caixa in lista_de_caixas_do_grupo:
        try:
            coordenada_interna = mapa_nomes_para_coordenadas[nome_caixa]
            coordenada_mapa = conversor_de_coordenadas_para_mapa.transform(*coordenada_interna)
            ponto_kml = pasta_caixas.newpoint(name=nome_caixa, coords=[coordenada_mapa])

            # Aplica um estilo diferente para a caixa central (hub)
            if nome_caixa == nome_da_caixa_hub:
                ponto_kml.style.iconstyle.color = simplekml.Color.green
                ponto_kml.style.iconstyle.scale = 1.2
            else:
                ponto_kml.style.iconstyle.color = simplekml.Color.yellow
                ponto_kml.style.iconstyle.scale = 1.0
        except KeyError:
            print(f"Aviso: A caixa '{nome_caixa}' não foi encontrada no mapa de coordenadas e será ignorada.")
        except Exception as e:
            print(f"Erro ao processar a caixa '{nome_caixa}': {e}")

    # 4. Salva o arquivo KML se um caminho de saída for especificado
    if arquivo_de_saida_kml:
        try:
            documento_kml_existente.save(arquivo_de_saida_kml)
            print(f"KML de saída gerado com sucesso: {arquivo_de_saida_kml}")
        except Exception as e:
            print(f"Erro ao salvar o arquivo KML em '{arquivo_de_saida_kml}': {e}")


## OTIMIZAÇÃO: Nova função para diagnosticar componentes desconectados
def exportar_componentes_desconectados_kml(
        rede_grafo: nx.Graph,
        conversor_de_coordenadas_para_mapa: Transformer,
        caminho_arquivo_saida: str
):
    """
    Gera um arquivo KML para visualizar os componentes desconectados de um grafo.
    Cada componente (ilha) será desenhado com uma cor diferente.

    Args:
        rede_grafo: O grafo da rede (potencialmente desconectado).
        conversor_de_coordenadas_para_mapa: O transformer do pyproj para converter de volta para Lat/Lon.
        caminho_arquivo_saida: O nome do arquivo KML de diagnóstico a ser salvo.
    """
    print(f"Exportando KML de diagnóstico para '{caminho_arquivo_saida}'...")

    # Encontra todos os componentes (ilhas) do grafo
    componentes = list(nx.connected_components(rede_grafo))
    componentes.sort(key=len, reverse=True)  # Ordena do maior para o menor

    kml = simplekml.Kml()

    # Define uma lista de cores para diferenciar os componentes
    cores = [
        simplekml.Color.red, simplekml.Color.blue, simplekml.Color.green,
        simplekml.Color.yellow, simplekml.Color.purple, simplekml.Color.orange,
        simplekml.Color.cyan, simplekml.Color.magenta, simplekml.Color.white,
        simplekml.Color.lightblue, simplekml.Color.lightgreen, simplekml.Color.brown,
        simplekml.Color.darkorange, simplekml.Color.darkgreen, simplekml.Color.pink
    ]

    # Itera sobre cada componente encontrado
    for i, componente_nodes in enumerate(componentes):
        # Cria um subgrafo contendo apenas os nós e arestas deste componente
        subgrafo = rede_grafo.subgraph(componente_nodes)

        # Cria uma pasta no KML para este componente
        pasta = kml.newfolder(name=f"Componente {i + 1} ({subgrafo.number_of_nodes()} nós)")

        # Seleciona uma cor para este componente
        cor_atual = cores[i % len(cores)]  # Usa o módulo para repetir as cores se houver mais componentes

        # Itera sobre cada aresta (linha) do componente
        for u, v in subgrafo.edges():
            try:
                # Converte as coordenadas dos pontos da aresta de volta para Lat/Lon
                ponto_u_geo = conversor_de_coordenadas_para_mapa.transform(*u)
                ponto_v_geo = conversor_de_coordenadas_para_mapa.transform(*v)

                # Desenha a linha no KML
                linestring = pasta.newlinestring(name=f"Aresta {i}")
                linestring.coords = [ponto_u_geo, ponto_v_geo]
                linestring.style.linestyle.color = cor_atual
                linestring.style.linestyle.width = 4  # Largura maior para melhor visualização
            except Exception as e:
                print(f"Aviso: Erro ao processar uma aresta no componente {i + 1}: {e}")

    kml.save(caminho_arquivo_saida)
    print(f"✅ KML de diagnóstico salvo. Abra-o no Google Earth para ver as 'ilhas' da rede.")


## OTIMIZAÇÃO: Nova função para diagnosticar componentes desconectados
def exportar_componentes_desconectados_kml(
        rede_grafo: nx.Graph,
        conversor_de_coordenadas_para_mapa: Transformer,
        caminho_arquivo_saida: str
):
    """
    Gera um arquivo KML para visualizar os componentes desconectados de um grafo.
    Cada componente (ilha) será desenhado com uma cor diferente.

    Args:
        rede_grafo: O grafo da rede (potencialmente desconectado).
        conversor_de_coordenadas_para_mapa: O transformer do pyproj para converter de volta para Lat/Lon.
        caminho_arquivo_saida: O nome do arquivo KML de diagnóstico a ser salvo.
    """
    print(f"Exportando KML de diagnóstico para '{caminho_arquivo_saida}'...")

    # Encontra todos os componentes (ilhas) do grafo
    componentes = list(nx.connected_components(rede_grafo))
    componentes.sort(key=len, reverse=True)  # Ordena do maior para o menor

    kml = simplekml.Kml()

    # Define uma lista de cores para diferenciar os componentes
    cores = [
        simplekml.Color.red, simplekml.Color.blue, simplekml.Color.green,
        simplekml.Color.yellow, simplekml.Color.purple, simplekml.Color.orange,
        simplekml.Color.cyan, simplekml.Color.magenta, simplekml.Color.white,
        simplekml.Color.lightblue, simplekml.Color.lightgreen, simplekml.Color.brown,
        simplekml.Color.darkorange, simplekml.Color.darkgreen, simplekml.Color.pink
    ]

    # Itera sobre cada componente encontrado
    for i, componente_nodes in enumerate(componentes):
        # Cria um subgrafo contendo apenas os nós e arestas deste componente
        subgrafo = rede_grafo.subgraph(componente_nodes)

        # Cria uma pasta no KML para este componente
        pasta = kml.newfolder(name=f"Componente {i + 1} ({subgrafo.number_of_nodes()} nós)")

        # Seleciona uma cor para este componente
        cor_atual = cores[i % len(cores)]  # Usa o módulo para repetir as cores se houver mais componentes

        # Itera sobre cada aresta (linha) do componente
        for u, v in subgrafo.edges():
            try:
                # Converte as coordenadas dos pontos da aresta de volta para Lat/Lon
                ponto_u_geo = conversor_de_coordenadas_para_mapa.transform(*u)
                ponto_v_geo = conversor_de_coordenadas_para_mapa.transform(*v)

                # Desenha a linha no KML
                linestring = pasta.newlinestring(name=f"Aresta {i}")
                linestring.coords = [ponto_u_geo, ponto_v_geo]
                linestring.style.linestyle.color = cor_atual
                linestring.style.linestyle.width = 4  # Largura maior para melhor visualização
            except Exception as e:
                print(f"Aviso: Erro ao processar uma aresta no componente {i + 1}: {e}")

    kml.save(caminho_arquivo_saida)
    print(f"✅ KML de diagnóstico salvo. Abra-o no Google Earth para ver as 'ilhas' da rede.")
