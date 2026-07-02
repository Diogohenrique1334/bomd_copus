"""Geração da arte "Melhor em Campo" para postar no Instagram (PNG 1080×1080).

É imagem raster com a identidade do BDC (dourado/preto), montada com Pillow — não
é um gráfico ECharts, por isso fica local no projeto (e não no Baltazar, que é a
fonte única só dos gráficos interativos). O dashboard chama `gerar_arte_mvp(...)`
e entrega os bytes num `st.download_button`.
"""
from __future__ import annotations

from datetime import date, datetime
from io import BytesIO
from typing import Optional

from PIL import Image, ImageDraw, ImageFont

# ── Identidade visual ────────────────────────────────────────────────────────
TAM = 1080
COR_FUNDO = (13, 13, 15)      # quase preto
COR_FUNDO2 = (26, 26, 34)     # cartão interno
COR_BDC = (212, 175, 55)      # dourado #D4AF37
COR_TEXTO = (240, 240, 240)
COR_SUB = (150, 150, 160)

# Fontes candidatas (bold) comuns em Linux/Windows; cai para a DejaVu embutida
# do Pillow quando nenhuma existe (mantém a arte funcionando em qualquer deploy).
_FONTES_BOLD = [
    "DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "C:/Windows/Fonts/arialbd.ttf",
    "arialbd.ttf",
]


def _fonte(tamanho: int) -> ImageFont.FreeTypeFont:
    for caminho in _FONTES_BOLD:
        try:
            return ImageFont.truetype(caminho, tamanho)
        except OSError:
            continue
    try:
        return ImageFont.load_default(size=tamanho)   # Pillow >= 10.1
    except TypeError:
        return ImageFont.load_default()


def _centralizar_x(draw: ImageDraw.ImageDraw, texto: str, y: int,
                   fonte: ImageFont.ImageFont, cor, stroke=0, stroke_cor=None) -> None:
    l, t, r, b = draw.textbbox((0, 0), texto, font=fonte, stroke_width=stroke)
    x = (TAM - (r - l)) // 2
    draw.text((x, y), texto, font=fonte, fill=cor,
              stroke_width=stroke, stroke_fill=stroke_cor)


def _foto_circular(foto_bytes: bytes, diametro: int) -> Image.Image:
    """Recorta a foto num círculo do diâmetro pedido (crop central quadrado)."""
    img = Image.open(BytesIO(foto_bytes)).convert("RGB")
    lado = min(img.size)
    esq = (img.width - lado) // 2
    topo = (img.height - lado) // 2
    img = img.crop((esq, topo, esq + lado, topo + lado)).resize(
        (diametro, diametro), Image.LANCZOS
    )
    mascara = Image.new("L", (diametro, diametro), 0)
    ImageDraw.Draw(mascara).ellipse((0, 0, diametro, diametro), fill=255)
    circular = Image.new("RGBA", (diametro, diametro), (0, 0, 0, 0))
    circular.paste(img, (0, 0), mascara)
    return circular


def _placeholder_circular(iniciais: str, diametro: int) -> Image.Image:
    """Círculo com as iniciais do atleta (quando não há foto)."""
    circulo = Image.new("RGBA", (diametro, diametro), (0, 0, 0, 0))
    d = ImageDraw.Draw(circulo)
    d.ellipse((0, 0, diametro, diametro), fill=COR_FUNDO2)
    fonte = _fonte(int(diametro * 0.42))
    l, t, r, b = d.textbbox((0, 0), iniciais, font=fonte)
    d.text(((diametro - (r - l)) / 2 - l, (diametro - (b - t)) / 2 - t),
           iniciais, font=fonte, fill=COR_BDC)
    return circulo


def _iniciais(apelido: str) -> str:
    partes = [p for p in (apelido or "?").split() if p]
    if not partes:
        return "?"
    if len(partes) == 1:
        return partes[0][:2].upper()
    return (partes[0][0] + partes[-1][0]).upper()


def _fmt_data(data) -> str:
    if isinstance(data, (date, datetime)):
        return data.strftime("%d/%m/%Y")
    try:
        return datetime.fromisoformat(str(data)[:10]).strftime("%d/%m/%Y")
    except ValueError:
        return str(data)


def gerar_arte_mvp(
    apelido: str,
    nota: float,
    adversario: str,
    data,
    foto_bytes: Optional[bytes] = None,
) -> bytes:
    """Monta a arte quadrada do melhor em campo e devolve os bytes do PNG."""
    img = Image.new("RGB", (TAM, TAM), COR_FUNDO)
    draw = ImageDraw.Draw(img)

    # Moldura dourada
    draw.rectangle((28, 28, TAM - 28, TAM - 28), outline=COR_BDC, width=6)

    # Cabeçalho
    _centralizar_x(draw, "MELHOR EM CAMPO", 96, _fonte(64), COR_BDC)
    _centralizar_x(draw, "B D C", 176, _fonte(34), COR_SUB)

    # Foto (ou placeholder) com anel dourado
    diametro = 440
    cx = TAM // 2
    topo_foto = 250
    anel = 12
    draw.ellipse(
        (cx - diametro // 2 - anel, topo_foto - anel,
         cx + diametro // 2 + anel, topo_foto + diametro + anel),
        fill=COR_BDC,
    )
    if foto_bytes:
        retrato = _foto_circular(foto_bytes, diametro)
    else:
        retrato = _placeholder_circular(_iniciais(apelido), diametro)
    img.paste(retrato, (cx - diametro // 2, topo_foto), retrato)

    # Nome
    _centralizar_x(draw, (apelido or "?").upper(), 760, _fonte(88), COR_TEXTO)

    # Nota em destaque
    _centralizar_x(draw, f"NOTA {nota:.1f}".replace(".", ","), 872,
                   _fonte(72), COR_BDC)

    # Rodapé: adversário e data
    _centralizar_x(draw, f"vs {adversario}  ·  {_fmt_data(data)}", 972,
                   _fonte(40), COR_SUB)

    buffer = BytesIO()
    img.save(buffer, format="PNG")
    return buffer.getvalue()
