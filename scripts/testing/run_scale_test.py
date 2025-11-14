"""Run discovery with larger scale for new sources."""

import subprocess
import sys
from pathlib import Path

# Add src to path
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path.parent))

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

console = Console()

# Database path
DB_PATH = "sqlite:///data/test_new_sources.sqlite"
MAX_RECORDS = 200

def run_discovery(source: str, max_records: int):
    """Run discovery for a source."""
    console.print(f"\n[bold cyan]Running {source} discovery (max_records={max_records})...[/bold cyan]")
    
    cmd = [
        sys.executable,
        "-m", "src.uwss.cli",
        f"{source}-lib-discover",
        "--max", str(max_records),
        "--db-url", DB_PATH,
    ]
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace"
        )
        
        if result.returncode == 0:
            console.print(f"[green][OK] {source} discovery completed[/green]")
            if result.stdout:
                # Show last few lines of output
                lines = result.stdout.strip().split("\n")
                for line in lines[-5:]:
                    if line.strip():
                        console.print(f"  {line}")
        else:
            console.print(f"[red][FAIL] {source} discovery failed[/red]")
            if result.stderr:
                console.print(f"[red]Error: {result.stderr}[/red]")
            return False
        return True
    except Exception as e:
        console.print(f"[red][FAIL] Error running {source}: {e}[/red]")
        return False

def main():
    """Main function."""
    console.print(f"[bold green]Starting scale test with max_records={MAX_RECORDS} per source[/bold green]")
    console.print(f"Database: {DB_PATH}\n")
    
    sources = ["crossref", "openalex", "semantic-scholar"]
    results = {}
    
    for source in sources:
        success = run_discovery(source, MAX_RECORDS)
        results[source] = success
    
    # Summary
    console.print("\n[bold cyan]=== SUMMARY ===[/bold cyan]")
    for source, success in results.items():
        status = "[green][OK] Success[/green]" if success else "[red][FAIL] Failed[/red]"
        console.print(f"  {source}: {status}")
    
    console.print("\n[bold green]Test completed! Run 'python test_scale_larger.py' to analyze results.[/bold green]")

if __name__ == "__main__":
    main()

