def build_theme_variables(theme: dict[str, str]) -> str:
    declarations = [f"--{key}: {value};" for key, value in sorted(theme.items())]
    return ":root {\n  " + "\n  ".join(declarations) + "\n}"

