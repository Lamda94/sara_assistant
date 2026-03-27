#!/usr/bin/env python3
"""Cliente CLI para conversar con SARA."""

import httpx
import sys
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

BACKEND_URL = "http://localhost:8000"
SESSION_ID = "cli-session-001"
DEVICE = "cli"

console = Console()


def print_banner():
    console.print(Panel(
        "[bold cyan]S A R A[/bold cyan]\n[dim]Sistema de Asistencia con Reconocimiento Adaptativo[/dim]\n[dim]Escribe 'salir' para terminar · 'memoria' para ver recuerdos[/dim]",
        border_style="cyan",
        expand=False,
    ))


def chat(message: str) -> str:
    with httpx.Client(timeout=30.0) as client:
        response = client.post(
            f"{BACKEND_URL}/chat",
            json={"message": message, "session_id": SESSION_ID, "device": DEVICE},
        )
        response.raise_for_status()
        return response.json()["response"]


def show_memories():
    with httpx.Client(timeout=10.0) as client:
        response = client.get(f"{BACKEND_URL}/memory")
        response.raise_for_status()
        data = response.json()

    console.print(f"\n[bold yellow]Recuerdos almacenados: {data['total']}[/bold yellow]")
    for m in data["memories"]:
        role_color = "green" if m["role"] == "user" else "blue"
        console.print(f"  [{role_color}]{m['role']:10}[/{role_color}] [{m['device']}] {m['content'][:80]}...")
    console.print()


def check_backend():
    try:
        with httpx.Client(timeout=5.0) as client:
            r = client.get(f"{BACKEND_URL}/health")
            r.raise_for_status()
        return True
    except Exception:
        return False


def main():
    print_banner()

    if not check_backend():
        console.print("[bold red]✗ No se puede conectar al backend.[/bold red]")
        console.print("  Asegúrate de que el servidor esté corriendo:")
        console.print("  [dim]cd backend && uvicorn app.main:app --reload[/dim]\n")
        sys.exit(1)

    console.print("[green]✓ Conectado a SARA[/green]\n")

    while True:
        try:
            user_input = console.input("[bold white]Tú:[/bold white] ").strip()
        except (KeyboardInterrupt, EOFError):
            console.print("\n[dim]Hasta luego.[/dim]")
            break

        if not user_input:
            continue

        if user_input.lower() in ("salir", "exit", "quit"):
            console.print("[dim]Hasta luego.[/dim]")
            break

        if user_input.lower() == "memoria":
            show_memories()
            continue

        try:
            with console.status("[dim]SARA está pensando...[/dim]"):
                response = chat(user_input)
            console.print(f"[bold cyan]SARA:[/bold cyan] {response}\n")
        except httpx.HTTPError as e:
            console.print(f"[red]Error al comunicarse con el backend: {e}[/red]\n")


if __name__ == "__main__":
    main()
