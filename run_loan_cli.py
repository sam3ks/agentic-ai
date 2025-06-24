import click
from agentic_ai.modules.loan_processing.app.cli import process_loan_application

def main():
    while True:
        request = click.prompt('Enter your loan request')
        if request.strip().lower() in ['stop', 'exit', 'quit']:
            print('Exiting loan processing. Goodbye!')
            break
        process_loan_application(request)

if __name__ == "__main__":
    main()
