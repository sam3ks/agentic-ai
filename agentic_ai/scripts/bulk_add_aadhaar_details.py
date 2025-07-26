import requests

# Sample data with your specified Aadhaar numbers
data = [
    {
        "aadhaar_number": "631999289535",
        "name": "Rajesh Kumar",
        "age": 35,
        "marital_status": "Married",
        "gender": "Male"
    },
    {
        "aadhaar_number": "263955468941",
        "name": "Priya Sharma",
        "age": 28,
        "marital_status": "Single",
        "gender": "Female"
    },
    {
        "aadhaar_number": "216563686675",
        "name": "Amit Patel",
        "age": 42,
        "marital_status": "Married",
        "gender": "Male"
    },
    {
        "aadhaar_number": "747356461632",
        "name": "Sunita Singh",
        "age": 31,
        "marital_status": "Married",
        "gender": "Female"
    },
    {
        "aadhaar_number": "096193980326",
        "name": "Vikram Reddy",
        "age": 39,
        "marital_status": "Married",
        "gender": "Male"
    },
    {
        "aadhaar_number": "467580848845",
        "name": "Meera Nair",
        "age": 26,
        "marital_status": "Single",
        "gender": "Female"
    },
    {
        "aadhaar_number": "246535477153",
        "name": "Arjun Gupta",
        "age": 33,
        "marital_status": "Single",
        "gender": "Male"
    },
    {
        "aadhaar_number": "503153508818",
        "name": "Kavita Joshi",
        "age": 45,
        "marital_status": "Married",
        "gender": "Female"
    },
    {
        "aadhaar_number": "347676851687",
        "name": "Rahul Sharma",
        "age": 30,
        "marital_status": "Single",
        "gender": "Male"
    }
]

def add_all_aadhaar_details():
    url = "http://localhost:5002/add_aadhaar_details"
    
    success_count = 0
    error_count = 0
    
    for person in data:
        try:
            response = requests.post(url, json=person)
            if response.status_code == 200:
                print(f"✓ Added details for {person['name']} (Aadhaar: {person['aadhaar_number']})")
                success_count += 1
            else:
                print(f"✗ Failed to add {person['name']}: {response.text}")
                error_count += 1
        except Exception as e:
            print(f"✗ Error adding {person['name']}: {str(e)}")
            error_count += 1
    
    print(f"\n--- Summary ---")
    print(f"Successfully added: {success_count} records")
    print(f"Failed: {error_count} records")
    print(f"Total processed: {len(data)} records")

if __name__ == "__main__":
    print("Adding Aadhaar details to database...")
    print("Make sure the Aadhaar Details API server is running on port 5002")
    print("You can start it with: python aadhaar_details_api.py")
    print("-" * 50)
    add_all_aadhaar_details()
