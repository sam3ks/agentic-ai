workspace "Agentic Loan Processing System" "C4 Architecture for AI-powered loan processing system based on actual codebase" {

    model {
        # People
        customer = person "Loan Applicant" "Person applying for a loan through the system"
        loanOfficer = person "Loan Officer" "Reviews and approves loan applications"
        admin = person "System Admin" "Manages system configuration and monitoring"

        # External Systems
        creditBureau = softwareSystem "Credit Bureau API" "External credit scoring service" "External"
        aadhaarSystem = softwareSystem "Aadhaar Verification System" "Government identity verification service" "External"
        llmProvider = softwareSystem "LLM Provider" "AI language model services (Groq/OpenAI/Ollama)" "External"

        # Main System
        loanSystem = softwareSystem "Agentic Loan Processing System" "AI-powered loan processing system using single agent with multiple tools" {
            
            # Containers
            webApp = container "Streamlit Web Application" "User interface for loan applications" "Python/Streamlit" "WebApp"
            
            orchestrator = container "Loan Agent Orchestrator" "Central coordinator using single agent executor with tools" "Python/LangChain" "Orchestrator" {
                # Core Orchestration Components
                loanOrchestrator = component "LoanAgentOrchestrator" "Main class that coordinates entire workflow using tools" "Python Class"
                agentExecutor = component "Agent Executor" "Single LangChain agent that uses all tools sequentially" "LangChain AgentExecutor"
                
                # Agent Service Classes (not separate executors)
                dataQueryAgent = component "DataQueryAgent" "Service for retrieving customer data from database" "Python Service"
                userInteractionAgent = component "UserInteractionAgent" "Service for handling customer communication" "Python Service"
                riskAssessmentAgent = component "RiskAssessmentAgent" "Service for evaluating creditworthiness and loan risk" "Python Service"
                geoPolicyAgent = component "GeoPolicyAgent" "Service for checking location-based loan policies" "Python Service"
                agreementAgent = component "AgreementAgent" "Service for generating and presenting loan agreements" "Python Service"
                purposeAgent = component "LoanPurposeAssessmentAgent" "Service for validating loan purposes against policies" "Python Service"
                pdfExtractorAgent = component "PDFSalaryExtractorAgent" "Service for extracting salary data from PDF documents" "Python Service"
                salaryGeneratorAgent = component "SalarySheetGeneratorAgent" "Fallback service for generating salary data" "Python Service"
                customerAgent = component "CustomerAgent" "Automated customer simulation for testing" "Python Service"
                
                # Tool Wrappers (what the agent executor actually uses)
                userInteractionTool = component "UserInteraction Tool" "Wrapped UserInteractionAgent as LangChain tool" "LangChain Tool"
                dataQueryTool = component "DataQuery Tool" "Wrapped DataQueryAgent as LangChain tool" "LangChain Tool"
                riskAssessmentTool = component "RiskAssessment Tool" "Wrapped RiskAssessmentAgent as LangChain tool" "LangChain Tool"
                geoPolicyTool = component "GeoPolicyCheck Tool" "Wrapped GeoPolicyAgent as LangChain tool" "LangChain Tool"
                agreementTool = component "AgreementPresentation Tool" "Wrapped AgreementAgent as LangChain tool" "LangChain Tool"
                purposeTool = component "LoanPurposeAssessment Tool" "Wrapped LoanPurposeAssessmentAgent as LangChain tool" "LangChain Tool"
                pdfExtractorTool = component "PDFSalaryExtractor Tool" "Wrapped PDFSalaryExtractorAgent as LangChain tool" "LangChain Tool"
                creditScoreTool = component "CreditScoreByPAN Tool" "Tool for fetching credit scores by PAN number" "LangChain Tool"
                validatePANTool = component "ValidatePANAadhaar Tool" "Tool for validating PAN-Aadhaar security match" "LangChain Tool"
                salaryGeneratorTool = component "SalarySheetGenerator Tool" "Wrapped SalarySheetGeneratorAgent as LangChain tool" "LangChain Tool"
                
                # Core Data Service
                loanDataService = component "LoanDataService" "Central data access service for all loan-related data" "Python Service"
                
                # Input/Output Management
                streamlitInputProvider = component "StreamlitInputProvider" "Manages communication between Streamlit UI and agents" "Python Component"
            }
            
            creditAPI = container "Credit Score API" "Internal credit scoring service" "Python/Flask"
            aadhaarAPI = container "Aadhaar API" "Identity verification service" "Python/Flask"
            database = container "SQLite Database" "Stores user data and loan records" "SQLite"
            fileStorage = container "File Storage" "Stores uploaded loan documents" "Local Filesystem"
        }

        # Relationships - People to System
        customer -> webApp "Submits loan applications and uploads documents"
        loanOfficer -> webApp "Reviews applications and makes decisions"
        admin -> webApp "Manages system configuration"

        # Relationships - System to External
        creditAPI -> creditBureau "Fetches external credit scores"
        aadhaarAPI -> aadhaarSystem "Verifies identity with government system"
        agentExecutor -> llmProvider "AI processing and natural language understanding"

        # Relationships - Container Level
        webApp -> loanOrchestrator "Sends user requests for processing"
        webApp -> streamlitInputProvider "Manages UI communication"
        loanOrchestrator -> agentExecutor "Coordinates workflow using single agent executor"
        loanOrchestrator -> streamlitInputProvider "Uses for user interaction management"
        
        # Agent Executor uses Tools (this is the key architecture - single agent, multiple tools)
        agentExecutor -> userInteractionTool "Uses for user communication"
        agentExecutor -> dataQueryTool "Uses for data retrieval"
        agentExecutor -> riskAssessmentTool "Uses for risk evaluation"
        agentExecutor -> geoPolicyTool "Uses for location policy checks"
        agentExecutor -> agreementTool "Uses for loan agreement generation"
        agentExecutor -> purposeTool "Uses for purpose validation"
        agentExecutor -> pdfExtractorTool "Uses for PDF salary processing"
        agentExecutor -> creditScoreTool "Uses for credit score lookup"
        agentExecutor -> validatePANTool "Uses for PAN-Aadhaar validation"
        agentExecutor -> salaryGeneratorTool "Uses as fallback for salary generation"
        
        # Tools delegate to Agent Services (the actual business logic)
        userInteractionTool -> userInteractionAgent "Delegates user communication to"
        dataQueryTool -> dataQueryAgent "Delegates data queries to"
        riskAssessmentTool -> riskAssessmentAgent "Delegates risk evaluation to"
        geoPolicyTool -> geoPolicyAgent "Delegates policy checks to"
        agreementTool -> agreementAgent "Delegates agreement generation to"
        purposeTool -> purposeAgent "Delegates purpose validation to"
        pdfExtractorTool -> pdfExtractorAgent "Delegates PDF processing to"
        salaryGeneratorTool -> salaryGeneratorAgent "Delegates salary generation to"
        
        # Service Dependencies
        dataQueryAgent -> loanDataService "Uses for data access"
        riskAssessmentAgent -> loanDataService "Uses for data access"
        salaryGeneratorAgent -> loanDataService "Uses for data storage"
        geoPolicyAgent -> loanDataService "Uses for policy data"
        
        # External API calls through services
        creditScoreTool -> creditAPI "Calls for credit scores"
        dataQueryAgent -> aadhaarAPI "Calls for identity verification"
        
        # Data persistence (all DB access via APIs, not orchestrator)
        creditAPI -> database "Queries and updates credit data"
        aadhaarAPI -> database "Queries and updates identity data"
        pdfExtractorAgent -> fileStorage "Reads uploaded salary documents"
        webApp -> fileStorage "Uploads user documents"
        
        # User Interaction Management
        userInteractionAgent -> streamlitInputProvider "Uses for UI communication"
        streamlitInputProvider -> webApp "Sends responses to UI"
    }

    views {
        systemContext loanSystem "SystemContext" {
            include *
            autolayout lr
            description "System context diagram showing the Agentic Loan Processing System and its external dependencies"
        }

        container loanSystem "Containers" {
            include *
            autolayout lr
            description "Container diagram showing the major applications and services within the loan processing system"
        }

        component orchestrator "OrchestratorComponents" {
            include *
            autolayout lr
            description "Component diagram showing the internal structure of the Loan Agent Orchestrator with single agent executor using multiple tools"
        }

        dynamic loanSystem "ContainerFlow" "Loan Application Processing at Container Level" {
            customer -> webApp "1. Submits loan application"
            webApp -> orchestrator "2. Initiates processing workflow"
            orchestrator -> creditAPI "3. Requests credit score"
            creditAPI -> creditBureau "4. Fetches external credit data"
            creditAPI -> database "5. Queries/updates credit data"
            orchestrator -> aadhaarAPI "6. Verifies identity"
            aadhaarAPI -> aadhaarSystem "7. Calls government verification"
            aadhaarAPI -> database "8. Queries/updates identity data"
            orchestrator -> webApp "9. Returns loan decision"
            webApp -> customer "10. Displays result"
            autolayout lr
            description "Shows the container-level flow of loan application processing"
        }

        dynamic orchestrator "ToolFlow" "Single Agent Executor Using Multiple Tools" {
            loanOrchestrator -> agentExecutor "1. Starts workflow coordination"
            agentExecutor -> userInteractionTool "2. Uses tool for user questions"
            userInteractionTool -> userInteractionAgent "3. Delegates to service"
            agentExecutor -> dataQueryTool "4. Uses tool for data retrieval"
            dataQueryTool -> dataQueryAgent "5. Delegates to service"
            agentExecutor -> purposeTool "6. Uses tool for purpose validation"
            agentExecutor -> riskAssessmentTool "7. Uses tool for risk assessment"
            riskAssessmentTool -> riskAssessmentAgent "8. Delegates to service"
            agentExecutor -> agreementTool "9. Uses tool for agreement generation"
            agreementTool -> agreementAgent "10. Delegates to service"
            agentExecutor -> loanOrchestrator "11. Returns final result"
            autolayout lr
            description "Shows how the single agent executor uses multiple tools sequentially for loan processing"
        }

        styles {
            element "Person" {
                color #ffffff
                background #08427b
                fontSize 22
                shape Person
            }
            element "External" {
                background #999999
                color #ffffff
            }
            element "WebApp" {
                background #1168bd
                color #ffffff
            }
            element "Orchestrator" {
                background #2e7d32
                color #ffffff
            }
            element "Database" {
                shape Cylinder
                background #f57c00
                color #ffffff
            }
            element "Component" {
                background #85bb65
                color #000000
            }
            relationship "Relationship" {
                color #707070
                dashed false
            }
        }
    }

    configuration {
        scope softwaresystem
    }
}
