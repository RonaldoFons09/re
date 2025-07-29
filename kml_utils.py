import os
import xml.etree.ElementTree as ET
from typing import List, Tuple, Dict
from shapely.geometry import LineString, Point

def carregar_kml_raiz(caminho_do_arquivo: str) -> ET.Element:
    """
    Carrega a raiz de um arquivo KML, tratando erros de arquivo não encontrado ou de parsing.
    """
    if not os.path.isfile(caminho_do_arquivo):
        raise FileNotFoundError(f"Arquivo não encontrado: {caminho_do_arquivo}")
    try:
        arvore_xml = ET.parse(caminho_do_arquivo)
        return arvore_xml.getroot()
    except ET.ParseError as e:
        raise ET.ParseError(f"Erro ao fazer parsing do arquivo KML {caminho_do_arquivo}: {e}")

def extrair_pontos_do_texto_de_coordenadas(texto_das_coordenadas: str) -> List[Tuple[float, float]]:
    """
    Converte uma string de coordenadas KML (ex: "-70,40,0 -71,41,0") para uma lista de pontos.
    """
    pontos: List[Tuple[float, float]] = []
    if not texto_das_coordenadas:
        return pontos

    # O texto vem como "lon1,lat1,alt1 lon2,lat2,alt2 ...", separamos por espaço.
    conjuntos_de_coordenadas = [conjunto for conjunto in texto_das_coordenadas.replace("\n", " ").split() if conjunto]
    for texto_do_ponto in conjuntos_de_coordenadas:
        try:
            partes = texto_do_ponto.split(",")
            if len(partes) >= 2:
                longitude = float(partes[0])
                latitude = float(partes[1])
                pontos.append((longitude, latitude))
        except (ValueError, IndexError) as e:
            print(f"Aviso: Coordenada com formato inválido '{texto_do_ponto}' será ignorada: {e}")
    return pontos

def extrair_geometrias_do_kml(
    raiz_kml: ET.Element,
    namespace_kml: Dict[str, str]
) -> Tuple[List[LineString], List[str], List[Tuple[Point, str]]]:
    """
    Extrai geometrias (LineStrings e Points) e seus nomes de um elemento raiz KML.

    A função percorre recursivamente os elementos KML, buscando por Placemarks
    em pastas com nomes específicos ('linhas_eletricas', 'caixas').
    """
    linhas_geograficas: List[LineString] = []
    nomes_das_linhas: List[str] = []
    caixas_com_nome: List[Tuple[Point, str]] = []

    def percorrer_elementos_kml(elemento_xml: ET.Element, caminho_da_pasta_atual: List[str]):
        """
        Função auxiliar recursiva para navegar na estrutura de pastas e placemarks do KML.
        """
        elemento_nome = elemento_xml.find('kml:name', namespace_kml)
        nome_da_pasta = elemento_nome.text.strip().lower().replace(' ', '_') if elemento_nome is not None and elemento_nome.text else ""
        novo_caminho_da_pasta = caminho_da_pasta_atual + [nome_da_pasta]
        caminho_completo = "/".join(novo_caminho_da_pasta)

        # Se o elemento atual for um Placemark, verifica se ele nos interessa
        if elemento_xml.tag.endswith('Placemark'):
            elemento_nome_placemark = elemento_xml.find('kml:name', namespace_kml)
            nome_do_placemark = elemento_nome_placemark.text.strip() if elemento_nome_placemark is not None and elemento_nome_placemark.text else "sem_nome"

            # Procura por linhas na pasta 'linhas_eletricas'
            if 'linhas_eletricas' in caminho_completo:
                elemento_linestring = elemento_xml.find(".//kml:LineString", namespace_kml)
                if elemento_linestring is not None:
                    elemento_coordenadas = elemento_linestring.find('kml:coordinates', namespace_kml)
                    if elemento_coordenadas is not None and elemento_coordenadas.text:
                        coordenadas = extrair_pontos_do_texto_de_coordenadas(elemento_coordenadas.text)
                        if len(coordenadas) >= 2:
                            linhas_geograficas.append(LineString(coordenadas))
                            nomes_das_linhas.append(nome_do_placemark)
                return # Já processamos este placemark, não precisa olhar os filhos

            # Procura por pontos na pasta 'caixas'
            if 'caixas' in caminho_completo:
                elemento_point = elemento_xml.find(".//kml:Point", namespace_kml)
                if elemento_point is not None:
                    elemento_coordenadas = elemento_point.find('kml:coordinates', namespace_kml)
                    if elemento_coordenadas is not None and elemento_coordenadas.text:
                        coordenadas = extrair_pontos_do_texto_de_coordenadas(elemento_coordenadas.text)
                        if coordenadas: # Se a lista não estiver vazia
                            ponto = Point(coordenadas[0])
                            caixas_com_nome.append((ponto, nome_do_placemark))
                return # Já processamos este placemark

        # Se não for um Placemark de interesse, continua a busca nos elementos filhos
        for elemento_filho in elemento_xml:
            percorrer_elementos_kml(elemento_filho, novo_caminho_da_pasta)

    percorrer_elementos_kml(raiz_kml, [])
    return linhas_geograficas, nomes_das_linhas, caixas_com_nome