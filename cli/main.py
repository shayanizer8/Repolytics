import asyncio
from typing import Any

import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress

from core.analyzer import full_analysis, full_comparison

app = typer.Typer()
console = Console()


def run_async(coro) -> Any:
    """Run an async coroutine synchronously."""
    return asyncio.run(coro)


def display_analysis(result: dict, title: str) -> None:
    """Display the full analysis result in a structured way using Rich."""
    
    meta = result.get("meta", {})
    repo_name = meta.get("name", "Unknown")
    repo_url = meta.get("url", "")
    health_score = result.get("health_score", 0)
    
    # 1. Header Panel with Health Score
    health_emoji = "🟢" if health_score >= 80 else "🟡" if health_score >= 50 else "🔴"
    health_status = "High" if health_score >= 80 else "Medium" if health_score >= 50 else "Low"
    header_text = f"[bold cyan]{repo_name}[/bold cyan]\n{repo_url}\n\n{health_emoji} {health_status} ({health_score})"
    console.print(Panel(header_text, title="Repository", border_style="cyan"))
    
    # 2. Tech Stack Table
    tech_stack = result.get("tech_stack", {})
    tech_table = Table(title="Tech Stack", show_header=True, header_style="bold magenta")
    tech_table.add_column("Property", style="cyan")
    tech_table.add_column("Value", style="green")
    tech_table.add_row("Language", tech_stack.get("language", "Unknown"))
    tech_table.add_row("Framework", tech_stack.get("framework", "Unknown"))
    tech_table.add_row("Has Tests", "✓" if tech_stack.get("has_tests") else "✗")
    tech_table.add_row("Has CI/CD", "✓" if tech_stack.get("has_ci") else "✗")
    tech_table.add_row("Containerized", "✓" if tech_stack.get("containerized") else "✗")
    tech_table.add_row("Database", tech_stack.get("database", "Unknown"))
    console.print(tech_table)
    
    # 3. Activity Table
    activity = result.get("activity", {})
    activity_table = Table(title="Activity", show_header=True, header_style="bold magenta")
    activity_table.add_column("Metric", style="cyan")
    activity_table.add_column("Value", style="green")
    activity_table.add_row("Stars", str(activity.get("stars", 0)))
    activity_table.add_row("Forks", str(activity.get("forks", 0)))
    activity_table.add_row("Open Issues", str(activity.get("open_issues", 0)))
    days_since = activity.get("days_since_commit")
    activity_table.add_row("Days Since Commit", str(days_since) if days_since is not None else "N/A")
    activity_table.add_row("Contributors", str(activity.get("contributor_count", 0)))
    activity_table.add_row("Is Active", "✓" if activity.get("is_active") else "✗")
    console.print(activity_table)
    
    # 4. Language Breakdown Table (top 5)
    languages = result.get("languages", {})
    if languages:
        sorted_langs = sorted(languages.items(), key=lambda x: x[1], reverse=True)[:5]
        lang_table = Table(title="Language Breakdown", show_header=True, header_style="bold magenta")
        lang_table.add_column("Language", style="cyan")
        lang_table.add_column("Percentage", style="green")
        for lang, percentage in sorted_langs:
            lang_table.add_row(lang, f"{percentage}%")
        console.print(lang_table)
    
    # 5. README Summary Panel
    readme_summary = result.get("readme_summary", {})
    if readme_summary:
        summary_text = f"[bold]Summary:[/bold]\n{readme_summary.get('summary', 'N/A')}\n\n"
        summary_text += f"[bold]Purpose:[/bold]\n{readme_summary.get('purpose', 'N/A')}\n\n"
        summary_text += f"[bold]Audience:[/bold]\n{readme_summary.get('audience', 'N/A')}"
        console.print(Panel(summary_text, title="README", border_style="green"))
    
    # 6. Code Smells Panel
    code_smells = result.get("code_smells", {})
    if code_smells:
        risk_level = code_smells.get("risk_level", "unknown").lower()
        risk_color = "green" if risk_level == "low" else "yellow" if risk_level == "medium" else "red"
        
        smells_text = f"[bold {risk_color}]Risk Level: {risk_level.upper()}[/bold {risk_color}]\n\n"
        
        flags = code_smells.get("flags", [])
        if flags:
            smells_text += "[bold]Flags:[/bold]\n"
            for flag in flags:
                smells_text += f"• {flag}\n"
        
        suggestions = code_smells.get("suggestions", [])
        if suggestions:
            smells_text += "\n[bold]Suggestions:[/bold]\n"
            for suggestion in suggestions:
                smells_text += f"• {suggestion}\n"
        
        console.print(Panel(smells_text, title="Code Smells", border_style=risk_color))


@app.command()
def analyze(
    url: str = typer.Argument(..., help="GitHub repository URL"),
    no_cache: bool = typer.Option(False, "--no-cache", help="Skip cache and fetch fresh data"),
    export: str = typer.Option(None, "--export", help="Export format: pdf or markdown"),
) -> None:
    """Analyze a repository."""
    try:
        with console.status(f"[bold cyan]Analyzing {url}...[/bold cyan]"):
            result = run_async(full_analysis(url, use_cache=not no_cache))
        display_analysis(result, title=url)
        
        if export:
            if export.lower() == "pdf":
                console.print("[yellow]PDF export coming in Phase 4[/yellow]")
            elif export.lower() == "markdown":
                console.print("[yellow]Markdown export coming in Phase 4[/yellow]")
            else:
                console.print(f"[red]Unknown export format: {export}[/red]")
                raise typer.Exit(code=1)
    except Exception as e:
        error_msg = str(e)
        if "not found" in error_msg.lower():
            console.print(f"[bold red]Repository not found: {url}[/bold red]")
        elif "rate limit" in error_msg.lower():
            console.print("[bold yellow]GitHub API rate limit hit. Try again later.[/bold yellow]")
        else:
            console.print(f"[bold red]Error: {error_msg}[/bold red]")
        raise typer.Exit(code=1)


@app.command()
def compare(
    url1: str = typer.Argument(..., help="First GitHub repository URL"),
    url2: str = typer.Argument(..., help="Second GitHub repository URL"),
    no_cache: bool = typer.Option(False, "--no-cache", help="Skip cache"),
) -> None:
    """Compare two repositories."""
    try:
        with console.status("[bold cyan]Comparing repositories...[/bold cyan]"):
            result = run_async(full_comparison(url1, url2, use_cache=not no_cache))
        
        # Display both repositories
        console.print("\n[bold cyan]Repository A:[/bold cyan]")
        display_analysis(result.get("repo_a", {}), title=url1)
        
        console.print("\n[bold cyan]Repository B:[/bold cyan]")
        display_analysis(result.get("repo_b", {}), title=url2)
        
        # Display Comparison Verdict Panel
        comparison = result.get("comparison", {})
        if comparison:
            winner = comparison.get("winner", "Tie")
            verdict = comparison.get("verdict", "")
            
            # Create reasoning table
            reasoning = comparison.get("reasoning", {})
            reasoning_table = Table(title="Comparison Reasoning", show_header=True, header_style="bold magenta")
            reasoning_table.add_column("Category", style="cyan")
            reasoning_table.add_column("Winner", style="green")
            reasoning_table.add_row("Activity", reasoning.get("activity", "—"))
            reasoning_table.add_row("Code Quality", reasoning.get("code_quality", "—"))
            reasoning_table.add_row("Community", reasoning.get("community", "—"))
            reasoning_table.add_row("Documentation", reasoning.get("documentation", "—"))
            
            verdict_text = f"[bold green]🏆 Winner: {winner}[/bold green]\n\n"
            verdict_text += f"{verdict}"
            
            console.print(Panel(verdict_text, title="Comparison Verdict", border_style="green"))
            console.print(reasoning_table)
    except Exception as e:
        error_msg = str(e)
        if "not found" in error_msg.lower():
            console.print(f"[bold red]Repository not found: {url1 if 'url1' in error_msg else url2}[/bold red]")
        elif "rate limit" in error_msg.lower():
            console.print("[bold yellow]GitHub API rate limit hit. Try again later.[/bold yellow]")
        else:
            console.print(f"[bold red]Error: {error_msg}[/bold red]")
        raise typer.Exit(code=1)


if __name__ == "__main__":
    app()
