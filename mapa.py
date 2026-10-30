"""Gera mapas de Goiás a partir de pontos em KMZ/KML (Google My Maps) usando geopandas.

Uso:
    python mapa.py config.yaml

Tudo que muda de um mapa para outro (arquivo de pontos, título, cores, destaques,
posição de rótulos) fica no YAML. Este arquivo só precisa ser editado para mudar
o "desenho" em si.
"""
import math
import sys
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path

import geopandas as gpd
import matplotlib.patheffects as pe
import matplotlib.pyplot as plt
import yaml
from matplotlib.lines import Line2D
from shapely.geometry import Point

NS = {"k": "http://www.opengis.net/kml/2.2"}
VIZINHOS = {"DF": (-47.80, -15.78), "MT": (-52.60, -14.60), "MS": (-52.60, -18.90),
            "MG": (-46.40, -17.25), "BA": (-45.90, -13.90), "TO": (-48.40, -12.75)}


# ---------------------------------------------------------------- leitura
def ler_kml(caminho: str) -> gpd.GeoDataFrame:
    """Lê KMZ ou KML e devolve pontos com colunas nome, descricao, camada."""
    caminho = Path(caminho)
    if caminho.suffix.lower() == ".kmz":
        with zipfile.ZipFile(caminho) as z:
            kml_nome = next(n for n in z.namelist() if n.lower().endswith(".kml"))
            raiz = ET.fromstring(z.read(kml_nome))
    else:
        raiz = ET.parse(caminho).getroot()

    linhas = []
    pastas = raiz.findall(".//k:Folder", NS) or [raiz]
    for pasta in pastas:
        camada = pasta.findtext("k:name", default="", namespaces=NS)
        for pm in pasta.findall(".//k:Placemark", NS):
            coord = pm.findtext(".//k:Point/k:coordinates", namespaces=NS)
            if not coord:
                continue  # ignora linhas/polígonos
            lon, lat = map(float, coord.strip().split(",")[:2])
            linhas.append({"nome": (pm.findtext("k:name", default="", namespaces=NS)).strip(),
                           "descricao": pm.findtext("k:description", default="", namespaces=NS),
                           "camada": camada, "geometry": Point(lon, lat)})
    return gpd.GeoDataFrame(linhas, crs="EPSG:4326")


def carregar_malhas(cfg):
    mun = gpd.read_file(cfg["malhas"]["municipios"]).set_crs("EPSG:4326", allow_override=True)
    uf = gpd.read_file(cfg["malhas"]["estados"]).to_crs("EPSG:4326")
    return mun, uf


# ---------------------------------------------------------------- desenho
def rotular(ax, pontos, cfg, cor_texto):
    rc = cfg.get("rotulos", {})
    if not rc.get("mostrar", True):
        return
    halo = [pe.withStroke(linewidth=2.2, foreground="white")]
    pos = rc.get("posicoes", {}) or {}
    dx = rc.get("deslocamento_padrao", 0.10)
    apelidos = rc.get("renomear", {}) or {}
    ocultar = set(rc.get("ocultar", []) or [])
    for _, r in pontos.iterrows():
        if r.nome in ocultar:
            continue
        px, py = r.geometry.x, r.geometry.y
        # padrão: à direita do ponto
        x, y, ha, guia = px + dx, py, "left", False
        if r.nome in pos:
            p = pos[r.nome]
            x, y = p["x"], p["y"]
            ha = p.get("alinhar", "left")
            guia = p.get("linha", False)
        if guia:
            ax.plot([px, x - (0.03 if ha == "left" else -0.03)], [py, y],
                    color="#7d8790", lw=0.45, zorder=4)
        destaque = r.nome in (cfg.get("destaques") or {})
        ax.text(x, y, apelidos.get(r.nome, r.nome), fontsize=rc.get("tamanho", 7.2),
                color=cor_texto, ha=ha, va="center", zorder=7, path_effects=halo,
                fontweight="bold" if destaque else "normal")


def escala_e_norte(ax, xmin, ymin, cor):
    ax.annotate("N", xy=(0.94, 0.955), xytext=(0.94, 0.89), xycoords="axes fraction",
                ha="center", fontsize=11, fontweight="bold", color=cor,
                arrowprops=dict(arrowstyle="-|>", color=cor, lw=1.4))
    x0, y0 = xmin - 0.25, ymin - 0.15
    dl = 100 / (111.32 * math.cos(math.radians(16)))  # 100 km em graus de longitude a 16°S
    ax.plot([x0, x0 + dl], [y0, y0], color=cor, lw=2.5, solid_capstyle="butt")
    ax.plot([x0, x0 + dl / 2], [y0, y0], color="white", lw=1.2, solid_capstyle="butt")
    ax.text(x0, y0 + 0.07, "0", fontsize=7, ha="center")
    ax.text(x0 + dl, y0 + 0.07, "100 km", fontsize=7, ha="center")


def gerar(cfg):
    c = {"texto": "#1f2933", "municipio": "#f3f1ec", "municipio_destacado": "#cfe3ef",
         "ponto": "#0b6e99", "fundo": "#e9eef2"}
    c.update(cfg.get("cores", {}) or {})

    pontos = ler_kml(cfg["pontos"])
    mun, uf = carregar_malhas(cfg)
    go = uf[uf.SIGLA == "GO"]

    # mantém só pontos dentro de Goiás (avisando os que ficaram fora)
    dentro = gpd.sjoin(pontos, go[["geometry"]], predicate="within").index
    fora = pontos.loc[~pontos.index.isin(dentro), "nome"].tolist()
    if fora:
        print("Aviso: pontos fora de Goiás (desenhados mesmo assim):", ", ".join(fora))

    plt.rcParams["font.family"] = "DejaVu Sans"
    fig, ax = plt.subplots(figsize=(10, 11), dpi=cfg.get("dpi", 300))
    fig.patch.set_facecolor("white")
    ax.set_facecolor(c["fundo"])

    uf[uf.SIGLA.isin(VIZINHOS)].plot(ax=ax, color="#fafafa", edgecolor="#b8bec4", linewidth=0.6)
    mun.plot(ax=ax, color=c["municipio"], edgecolor="#c9c4ba", linewidth=0.25)
    if cfg.get("pintar_municipios", True):
        ids = gpd.sjoin(mun, pontos, predicate="contains").id.unique()
        mun[mun.id.isin(ids)].plot(ax=ax, color=c["municipio_destacado"],
                                   edgecolor="#9fbfd3", linewidth=0.35)
        n_mun = len(ids)
    go.boundary.plot(ax=ax, color="#4a5560", linewidth=1.1)
    for sig, (x, y) in VIZINHOS.items():
        ax.text(x, y, sig, color="#8a9199", fontsize=9, ha="center", va="center", style="italic")

    # pontos comuns e destaques
    destaques = cfg.get("destaques") or {}
    comuns = pontos[~pontos.nome.isin(destaques)]
    comuns.plot(ax=ax, color=c["ponto"], markersize=28, edgecolor="white", linewidth=0.7, zorder=5)
    legenda = []
    for nome, d in destaques.items():
        sel = pontos[pontos.nome == nome]
        if sel.empty:
            print(f"Aviso: destaque '{nome}' não existe no arquivo de pontos")
            continue
        sel.plot(ax=ax, color=d.get("cor", "#c0392b"), marker=d.get("marcador", "*"),
                 markersize=190, edgecolor="white", linewidth=0.7, zorder=6)
        legenda.append(Line2D([0], [0], marker=d.get("marcador", "*"), color="w",
                              markerfacecolor=d.get("cor", "#c0392b"), markersize=14,
                              label=d.get("legenda", nome)))
    legenda.append(Line2D([0], [0], marker="o", color="w", markerfacecolor=c["ponto"],
                          markeredgecolor="white", markersize=7,
                          label=cfg.get("legenda_pontos", "Pontos").format(n=len(pontos), n_sem_destaque=len(comuns))))
    if cfg.get("pintar_municipios", True):
        legenda.append(Line2D([0], [0], marker="s", color="w", markerfacecolor=c["municipio_destacado"],
                              markeredgecolor="#9fbfd3", markersize=10,
                              label=cfg.get("legenda_municipios", "Município representado").format(n=n_mun, n_pontos=len(pontos))))

    rotular(ax, pontos, cfg, c["texto"])

    xmin, ymin, xmax, ymax = go.total_bounds
    ax.set_xlim(xmin - 0.45, xmax + 0.45)
    ax.set_ylim(ymin - 0.35, ymax + 0.35)
    ax.set_aspect(1 / math.cos(math.radians(16)))
    ax.tick_params(labelsize=7, colors="#6b7480")
    ax.set_xticks(range(-53, -45)); ax.set_yticks(range(-19, -12))
    ax.set_xticklabels([f"{abs(v)}°O" for v in range(-53, -45)])
    ax.set_yticklabels([f"{abs(v)}°S" for v in range(-19, -12)])
    ax.grid(color="white", linewidth=0.5, alpha=0.6); ax.set_axisbelow(True)
    for s in ax.spines.values():
        s.set_color("#9aa3ab")
    ax.set_xlabel(""); ax.set_ylabel("")

    escala_e_norte(ax, xmin, ymin, c["texto"])
    ax.legend(handles=legenda, loc="upper left", fontsize=7.5, frameon=True,
              framealpha=0.95, edgecolor="#c9c4ba")

    if cfg.get("localizador", True):
        ins = fig.add_axes([0.70, 0.14, 0.19, 0.19])
        uf.plot(ax=ins, color="#e4e1da", edgecolor="white", linewidth=0.3)
        go.plot(ax=ins, color=c["ponto"])
        ins.set_xticks([]); ins.set_yticks([]); ins.set_xlabel(""); ins.set_ylabel("")
        ins.set_facecolor("white")
        for s in ins.spines.values():
            s.set_color("#9aa3ab")

    ax.set_title(cfg.get("titulo", ""), fontsize=12.5, color=c["texto"], pad=12, fontweight="bold")
    if cfg.get("fonte"):
        fig.text(0.125, 0.085, cfg["fonte"], fontsize=6.5, color="#6b7480")

    saida = Path(cfg.get("saida", "saida/mapa"))
    saida.parent.mkdir(parents=True, exist_ok=True)
    for fmt in cfg.get("formatos", ["png", "pdf"]):
        fig.savefig(saida.with_suffix("." + fmt), bbox_inches="tight", facecolor="white")
        print("Gerado:", saida.with_suffix("." + fmt))

    if cfg.get("exportar_tabela", True):
        tab = pontos.assign(lon=pontos.geometry.x, lat=pontos.geometry.y)
        tab = gpd.sjoin(tab, mun[["name", "id", "geometry"]], how="left", predicate="within")
        tab = tab.rename(columns={"name": "municipio_ibge", "id": "cod_ibge"})
        tab[["nome", "camada", "municipio_ibge", "cod_ibge", "lat", "lon"]].to_csv(
            saida.with_suffix(".csv"), index=False)
        print("Gerado:", saida.with_suffix(".csv"))


if __name__ == "__main__":
    arq = sys.argv[1] if len(sys.argv) > 1 else "config.yaml"
    gerar(yaml.safe_load(open(arq, encoding="utf-8")))
