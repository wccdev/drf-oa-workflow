"""Console script for drf_oa_workflow."""

import click


@click.command()
def main():
    """Main entrypoint."""
    click.echo("wccoaworkflow")
    click.echo("=" * len("wccoaworkflow"))
    click.echo("Skeleton project created by Cookiecutter PyPackage")


if __name__ == "__main__":
    main()  # pragma: no cover
