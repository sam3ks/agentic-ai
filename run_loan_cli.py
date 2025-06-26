# import click
# from agentic_ai.modules.loan_processing.app.cli import process_loan_application
# import random

# def generate_random_profile():
#     purposes = ["home renovation", "education", "wedding", "business expansion", "medical"]
#     cities = ["Mumbai", "Delhi", "Bangalore", "Chennai", "Kolkata"]
#     amounts = ["100000", "250000", "500000", "750000", "1000000"]
#     pan_numbers = ["ABCDE1234F", "FGHIJ5678K", "KLMNO9012P", "AASIL9982X", "OHWQG0796D", "JPYVM1461B"]
#     aadhaar_numbers = ["123456789012", "234567890123", "345678901234", "503153508818", "347676851687", "776849406520"]
#     return {
#         "purpose": random.choice(purposes),
#         "amount": random.choice(amounts),
#         "city": random.choice(cities),
#         "identifier": random.choice(pan_numbers + aadhaar_numbers)
#     }

# def generate_automated_request(profile):
#     return f"I want a loan for {profile['purpose']} of amount {profile['amount']} in {profile['city']}."

# def main():
#     while True:
#         automate = click.confirm('Automate user input with CustomerAgent?', default=False)
#         if automate:
#             profile = generate_random_profile()
#             request = generate_automated_request(profile)
#             print(f"[CustomerAgent] Generated loan request: {request}")
#         else:
#             profile = None
#             request = click.prompt('Enter your loan request')
#         if request.strip().lower() in ['stop', 'exit', 'quit']:
#             print('Exiting loan processing. Goodbye!')
#             break
#         process_loan_application(request, automate_user=automate, customer_profile=profile)

# if __name__ == "__main__":
#     main()

#run_loan_cli.py
import click
from agentic_ai.modules.loan_processing.app.cli import process_loan_application
import random
import sys
 
def generate_random_profile():
    purposes = ["home renovation", "education", "wedding", "business expansion", "medical"]
    cities = ["Mumbai", "Delhi", "Bangalore", "Chennai", "Kolkata"]
    amounts = ["100000", "250000", "500000", "750000", "1000000"]
    pan_numbers = ["ABCDE1234F", "FGHIJ5678K", "KLMNO9012P", "AASIL9982X", "OHWQG0796D", "JPYVM1461B"]
    aadhaar_numbers = ["123456789012", "234567890123", "345678901234", "503153508818", "347676851687", "776849406520"]
    return {
        "purpose": random.choice(purposes),
        "amount": random.choice(amounts),
        "city": random.choice(cities),
        "identifier": random.choice(pan_numbers + aadhaar_numbers)
    }
 
def generate_automated_request(profile):
    return f"I want a loan for {profile['purpose']} of amount {profile['amount']} in {profile['city']}."
 
@click.command()
@click.option('--customer-agent', is_flag=True, help='Automate user input with CustomerAgent')
def main(customer_agent):
    if customer_agent:
        profile = generate_random_profile()
        request = generate_automated_request(profile)
        print(f"[CustomerAgent] Generated loan request: {request}")
        process_loan_application(request, automate_user=True, customer_profile=profile)
    else:
        while True:
            request = click.prompt('Enter your loan request')
            if request.strip().lower() in ['stop', 'exit', 'quit']:
                print('Exiting loan processing. Goodbye!')
                sys.exit(0)
            process_loan_application(request, automate_user=False, customer_profile=None)
 
if __name__ == "__main__":
    main()
 
 
