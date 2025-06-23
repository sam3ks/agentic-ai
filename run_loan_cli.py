import click
from agentic_ai.modules.loan_processing.app.cli import process_loan_application

@click.command()
@click.option('--request', prompt='Enter your loan request', help='Your loan application request')
def process(request):
    """Processes a loan application request."""
    process_loan_application(request)

if __name__ == "__main__":
    process()
