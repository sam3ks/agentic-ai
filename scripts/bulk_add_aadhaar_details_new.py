import requests

# Sample data with updated schema - removed marital_status, added address and dob
data = [
    {
        "aadhaar_number": "631999289535",
        "name": "Rajesh Kumar",
        "age": 35,
        "gender": "Male",
        "address": "123 MG Road, Bangalore, Karnataka 560001",
        "dob": "1988-03-15"
    },
    {
        "aadhaar_number": "263955468941",
        "name": "Priya Sharma",
        "age": 28,
        "gender": "Female",
        "address": "456 Park Street, Mumbai, Maharashtra 400001",
        "dob": "1995-07-22"
    },
    {
        "aadhaar_number": "216563686675",
        "name": "Amit Patel",
        "age": 42,
        "gender": "Male",
        "address": "789 Civil Lines, Delhi, NCR 110001",
        "dob": "1981-11-08"
    },
    {
        "aadhaar_number": "747356461632",
        "name": "Sunita Singh",
        "age": 31,
        "gender": "Female",
        "address": "321 Jubilee Hills, Hyderabad, Telangana 500033",
        "dob": "1992-02-14"
    },
    {
        "aadhaar_number": "096193980326",
        "name": "Vikram Reddy",
        "age": 39,
        "gender": "Male",
        "address": "567 Sector 15, Chandigarh, Punjab 160015",
        "dob": "1984-09-30"
    },
    {
        "aadhaar_number": "467580848845",
        "name": "Deepika Jain",
        "age": 31,
        "gender": "Female",
        "address": "890 Saket, New Delhi, NCR 110017",
        "dob": "1992-12-05"
    },
    {
        "aadhaar_number": "246535477153",
        "name": "Arjun Nair",
        "age": 26,
        "gender": "Male",
        "address": "234 Marine Drive, Kochi, Kerala 682001",
        "dob": "1997-05-18"
    },
    {
        "aadhaar_number": "503153508818",
        "name": "Meera Gupta",
        "age": 33,
        "gender": "Female",
        "address": "456 Salt Lake, Kolkata, West Bengal 700091",
        "dob": "1990-08-11"
    },
    {
        "aadhaar_number": "347676851687",
        "name": "Kavita Joshi",
        "age": 45,
        "gender": "Female",
        "address": "123 Koregaon Park, Pune, Maharashtra 411001",
        "dob": "1978-04-27"
    },
    {
        "aadhaar_number": "776849406520",
        "name": "Rahul Sharma",
        "age": 30,
        "gender": "Male",
        "address": "789 Banjara Hills, Hyderabad, Telangana 500034",
        "dob": "1993-10-12"
    },
    {
        "aadhaar_number": "960716235487",
        "name": "Anil Verma",
        "age": 27,
        "gender": "Male",
        "address": "12 Lajpat Nagar, New Delhi, NCR 110024",
        "dob": "1996-06-15"
    },
    {
        "aadhaar_number": "225812783128",
        "name": "Pooja Agarwal",
        "age": 32,
        "gender": "Female",
        "address": "67 Anna Nagar, Chennai, Tamil Nadu 600040",
        "dob": "1991-01-28"
    },
    {
        "aadhaar_number": "324444958446",
        "name": "Suresh Menon",
        "age": 41,
        "gender": "Male",
        "address": "89 Palayam, Thiruvananthapuram, Kerala 695033",
        "dob": "1982-12-03"
    },
    {
        "aadhaar_number": "683146775699",
        "name": "Ritu Kapoor",
        "age": 29,
        "gender": "Female",
        "address": "45 Model Town, Ludhiana, Punjab 141002",
        "dob": "1994-09-17"
    },
    {
        "aadhaar_number": "409177340269",
        "name": "Manish Tiwari",
        "age": 36,
        "gender": "Male",
        "address": "23 Gomti Nagar, Lucknow, Uttar Pradesh 226010",
        "dob": "1987-04-22"
    },
    {
        "aadhaar_number": "077234293155",
        "name": "Shruti Desai",
        "age": 25,
        "gender": "Female",
        "address": "78 FC Road, Pune, Maharashtra 411005",
        "dob": "1998-11-09"
    },
    {
        "aadhaar_number": "092791981126",
        "name": "Kiran Rao",
        "age": 38,
        "gender": "Male",
        "address": "34 Banjara Hills, Hyderabad, Telangana 500034",
        "dob": "1985-07-14"
    },
    {
        "aadhaar_number": "690013164323",
        "name": "Neha Sinha",
        "age": 33,
        "gender": "Female",
        "address": "56 Boring Road, Patna, Bihar 800001",
        "dob": "1990-03-26"
    },
    {
        "aadhaar_number": "796584533654",
        "name": "Vivek Gupta",
        "age": 44,
        "gender": "Male",
        "address": "91 Sector 18, Noida, Uttar Pradesh 201301",
        "dob": "1979-08-05"
    },
    {
        "aadhaar_number": "047759227363",
        "name": "Sanya Malhotra",
        "age": 26,
        "gender": "Female",
        "address": "12 Karol Bagh, New Delhi, NCR 110005",
        "dob": "1997-12-18"
    },
    {
        "aadhaar_number": "404582137488",
        "name": "Rohit Choudhary",
        "age": 31,
        "gender": "Male",
        "address": "45 C Scheme, Jaipur, Rajasthan 302001",
        "dob": "1992-05-11"
    },
    {
        "aadhaar_number": "512307192611",
        "name": "Kavya Pillai",
        "age": 28,
        "gender": "Female",
        "address": "78 Kakkanad, Kochi, Kerala 682030",
        "dob": "1995-02-07"
    },
    {
        "aadhaar_number": "138912347034",
        "name": "Arpit Joshi",
        "age": 35,
        "gender": "Male",
        "address": "23 Satellite, Ahmedabad, Gujarat 380015",
        "dob": "1988-10-29"
    },
    {
        "aadhaar_number": "184574694190",
        "name": "Tanvi Shah",
        "age": 24,
        "gender": "Female",
        "address": "67 Navrangpura, Ahmedabad, Gujarat 380009",
        "dob": "1999-06-21"
    },
    {
        "aadhaar_number": "259076892687",
        "name": "Abhishek Kumar",
        "age": 37,
        "gender": "Male",
        "address": "34 Frazer Road, Patna, Bihar 800001",
        "dob": "1986-01-16"
    },
    {
        "aadhaar_number": "425080685699",
        "name": "Isha Bhatt",
        "age": 30,
        "gender": "Female",
        "address": "89 Vastrapur, Ahmedabad, Gujarat 380015",
        "dob": "1993-09-04"
    },
    {
        "aadhaar_number": "840797530232",
        "name": "Siddharth Mehta",
        "age": 39,
        "gender": "Male",
        "address": "12 Vile Parle, Mumbai, Maharashtra 400057",
        "dob": "1984-11-13"
    },
    {
        "aadhaar_number": "170392872632",
        "name": "Anjali Reddy",
        "age": 27,
        "gender": "Female",
        "address": "45 Gachibowli, Hyderabad, Telangana 500032",
        "dob": "1996-04-08"
    },
    {
        "aadhaar_number": "338330401888",
        "name": "Nikhil Pandey",
        "age": 34,
        "gender": "Male",
        "address": "78 Hazratganj, Lucknow, Uttar Pradesh 226001",
        "dob": "1989-12-25"
    },
    {
        "aadhaar_number": "375687085459",
        "name": "Divya Iyer",
        "age": 32,
        "gender": "Female",
        "address": "23 Indiranagar, Bangalore, Karnataka 560038",
        "dob": "1991-07-30"
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
    print("Adding Aadhaar details to database with updated schema...")
    print("Schema changes: Removed marital_status, Added address and dob")
    print("Make sure the Aadhaar Details API server is running on port 5002")
    print("You can start it with: python aadhaar_details_api.py")
    print("-" * 50)
    add_all_aadhaar_details()
