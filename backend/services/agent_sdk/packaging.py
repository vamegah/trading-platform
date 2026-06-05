from pathlib import Path


def build_agent_package(agent_dir: str, output_dir: str = "dist") -> dict[str, str]:
    source = Path(agent_dir)
    target = Path(output_dir) / f"{source.name}.tar.gz"
    return {
        "source": str(source),
        "artifact": str(target),
        "status": "planned",
    }

