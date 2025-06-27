#pdf_salary_extractor.py
from agentic_ai.core.agent.base_agent import BaseAgent
from agentic_ai.modules.loan_processing.services.pdf_parser import PDFSalaryParser
import json
import os

class PDFSalaryExtractorAgent(BaseAgent):
    """Agent for extracting salary information from PDF files."""
    
    def __init__(self):
        super().__init__()
        self.pdf_parser = PDFSalaryParser()
        
    def run(self, file_path: str) -> str:
        """
        Extracts salary information from a PDF file.
        
        Args:
            file_path: Path to the PDF file
            
        Returns:
            JSON string containing the extracted salary information
        """
        print(f"📄 Processing salary information from PDF at: {file_path}")
        
        # ENHANCED PATH HANDLING        # Normalize the path and handle both relative and absolute paths
        # CRITICAL FIX: Clean the input string to extract just the file path
        # First, strip quotes
        file_path = file_path.strip().strip('"').strip("'")
        file_path = os.path.basename(file_path)  # Get just the filename if it's a full path
        # If there are newlines, only take the first line (the actual path)
        if '\n' in file_path:
            file_path = file_path.split('\n')[0].strip()
        print(f"[DEBUG] Raw file path: {file_path}")
        print(f"[DEBUG] File path repr: {repr(file_path)}")  # Show any invisible chars
        
        # Current working directory
        cwd = os.getcwd()
        print(f"[DEBUG] Current working directory: {cwd}")
        
        # Try multiple path variations to find the file
        possible_paths = [
            file_path,  # As provided
            os.path.normpath(file_path),  # Normalized path
            os.path.abspath(file_path),  # Absolute path
            os.path.join(cwd, file_path),  # Relative to CWD
            os.path.join(cwd, os.path.basename(file_path)),  # Just filename in CWD
            os.path.join(os.path.dirname(cwd), "agentic_ai", os.path.basename(file_path))  # File in agentic_ai folder
        ]
        
        file_found = False
        for path in possible_paths:
            print(f"[DEBUG] Trying path: {path}")
            if os.path.exists(path):
                print(f"[DEBUG] Found file at: {path}")
                file_path = path
                file_found = True
                break
                
        if not file_found:
            print(f"[DEBUG] File not found in expected locations, searching in project directories...")
            try:
                # Get the project root directory
                project_dir = os.path.abspath(os.path.join(cwd, ".."))
                filename = os.path.basename(file_path)
                
                # Check agentic_ai directory
                if os.path.exists(os.path.join(project_dir, "agentic_ai")):
                    ai_dir = os.path.join(project_dir, "agentic_ai")
                    ai_path = os.path.join(ai_dir, filename)
                    if os.path.exists(ai_path):
                        print(f"[DEBUG] Found file in agentic_ai directory: {ai_path}")
                        file_path = ai_path
                        file_found = True
                
                # List all directories in project for debugging
                if not file_found:
                    print(f"[DEBUG] Available directories in {project_dir}:")
                    for root, dirs, files in os.walk(project_dir, topdown=True, followlinks=False):
                        if filename in files:
                            found_path = os.path.join(root, filename)
                            print(f"[DEBUG] Found file: {found_path}")
                            file_path = found_path
                            file_found = True
                            break
                        print(f"  - {root}: {files}")
                        if len(dirs) + len(files) > 20:
                            # Don't print too many entries
                            break
            except Exception as e:
                print(f"[DEBUG] Error during extended file search: {str(e)}")
                
        if not file_found:
            parent_dir = os.path.dirname(file_path)
            print(f"[DEBUG] Directory listing for {parent_dir}:")
            try:
                print(os.listdir(parent_dir))
            except Exception as e:
                print(f"[DEBUG] Could not list directory: {e}")
            
            # Try to use the text file instead of PDF as fallback
            text_file_path = file_path.replace('.pdf', '.txt')
            if os.path.exists(text_file_path):
                print(f"[DEBUG] PDF not found, but text file exists at: {text_file_path}")
                file_path = text_file_path
                file_found = True
            else:
                print(f"WARNING: File does not exist at provided path , exploring alternatives...")
                return json.dumps({
                    "error": f"File not found: {file_path}. Please provide a valid path to a PDF file.",
                    "debug_cwd": os.getcwd(),
                    "debug_exists": os.path.exists(file_path),
                    "debug_parent_dir": parent_dir,
                    "tested_paths": possible_paths,
                    "fallback_needed": True
                })
          # Extract data from PDF
        extracted_data = self.pdf_parser.extract_from_pdf(file_path)
        # Format the data
        salary_sheet = self.pdf_parser.format_salary_sheet(extracted_data)
        
        if "error" in salary_sheet:
            return json.dumps({
                "error": salary_sheet["error"],
                "status": "pdf_extraction_failed",
                "fallback_needed": True,
                "suggestions": [
                    "Make sure the PDF contains salary or income information",
                    "Check if the PDF is properly formatted and not secured",
                    "Try providing a different salary document"                ]
            })
        
        print(f"✓ Successfully extracted salary information from PDF")
        # Add additional fields to make this compatible with RiskAssessment expectations
        salary_sheet["status"] = "pdf_extraction_successful"
        # Make sure we signal that no fallback is needed
        salary_sheet["fallback_needed"] = False
        
        # Extract key fields and add them to top level for RiskAssessment agent
        monthly_income = salary_sheet.get("salary_details", {}).get("monthly_income", 0)
        credit_score = salary_sheet.get("financial_health", {}).get("credit_score", 0)
        existing_emi = salary_sheet.get("financial_health", {}).get("existing_emi", 0)
        
        # Add user_data with the extracted information for RiskAssessment
        salary_sheet["user_data"] = {
            "monthly_salary": monthly_income,
            "credit_score": credit_score,
            "existing_emi": existing_emi,
            "employer": salary_sheet.get("salary_details", {}).get("employer", "Unknown"),
            "employment_type": salary_sheet.get("salary_details", {}).get("employment_type", "Salaried"),
            "source": "pdf_extraction"
        }
        
        return json.dumps(salary_sheet, indent=2)
