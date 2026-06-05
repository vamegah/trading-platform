def fair_value_score(symbol: str) -> float:
    seed = sum(ord(char) for char in symbol.upper())
    return round(0.52 + (seed % 30) / 100, 2)

