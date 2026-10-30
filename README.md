# mapa-goias

Gera mapas de Goiás (contorno estadual, malha municipal, estados vizinhos, localizador no Brasil,
escala e norte) a partir de pontos exportados do Google My Maps (KMZ/KML), com geopandas + matplotlib.

## Instalação

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Uso

```bash
python mapa.py config.yaml
```

Saídas em `saida/`: PNG (300 dpi), PDF e SVG vetoriais, e um CSV com cada ponto, o município
IBGE onde ele cai e o código IBGE (útil para cruzar com outras bases).

## Fazer outro mapa

1. Exporte a camada no My Maps: ⋮ → *Exportar para KML/KMZ* e coloque o arquivo em `dados/`.
2. Copie `config.yaml` (ex.: `config_romarias.yaml`) e troque `pontos`, `titulo`, `fonte`, `saida`.
3. Rode `python mapa.py config_romarias.yaml`.

O que se ajusta pelo YAML:

| Chave | Para quê |
|---|---|
| `destaques` | pontos com marcador/cor próprios e entrada na legenda |
| `rotulos.posicoes` | posição manual de rótulos (lon/lat), alinhamento e linha-guia |
| `rotulos.ocultar` | lista de pontos sem rótulo |
| `rotulos.renomear` | trocar o texto exibido sem mexer no KMZ |
| `rotulos.mostrar` | `false` para mapa só com marcadores |
| `legenda_pontos` | texto da legenda; `{n}` conta todos os pontos, `{n_sem_destaque}` exclui os destaques |
| `pintar_municipios` | preencher os municípios que contêm pontos |
| `cores`, `dpi`, `formatos`, `localizador` | aparência e saída |

Pontos sem posição definida recebem o rótulo à direita. Se rótulos se sobrepuserem, ajuste só
os pontos problemáticos em `rotulos.posicoes`.

## Estrutura

```
mapa.py              # leitura do KMZ e desenho
config.yaml          # mapa dos alunos e egressos do PROMEP
dados/
  alunos_egressos_promep.kmz
  go_municipios.geojson   # 246 municípios de Goiás
  br_estados.geojson      # UFs do Brasil
saida/
```

## Ideias de extensão

- **Mapa coroplético**: contar pontos por `cod_ibge` (do CSV) e colorir os municípios pela contagem.
- **Categorias**: se o My Maps tiver várias camadas (ex.: alunos × egressos), a coluna `camada`
  já vem preenchida e pode receber uma cor por camada.
- **Projeção**: para medir áreas e distâncias, reprojete para SIRGAS 2000 / Brazil Polyconic
  (`EPSG:5880`) com `.to_crs(5880)`.
- **Malhas oficiais atualizadas**: as malhas incluídas vêm do projeto
  [geodata-br](https://github.com/tbrugz/geodata-br) (derivadas do IBGE). Para usar a malha mais
  recente, baixe do IBGE (malhas territoriais, GO, municípios) ou use o pacote `geobr`
  (`geobr.read_municipality(code_muni="GO", year=2022)`) e aponte `malhas.municipios` para o
  arquivo. A coluna de código deve se chamar `id` e a de nome `name` (ou ajuste no código).
