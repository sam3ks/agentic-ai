workspace "Agentic Loan Processing - Complete C4 Overview" "All 4 C's in single diagram: Context, Container, Component, Code" {

    model {
        # LEVEL 1: CONTEXT - People and External Systems
        customer = person "👤 Loan Applicant" "Submits loan applications"
        loanOfficer = person "👤 Loan Officer" "Reviews applications" 
        admin = person "👤 System Admin" "Manages system"

        creditBureau = softwareSystem "🏢 Credit Bureau API" "External credit scoring" "External"
        aadhaarSystem = softwareSystem "🏛️ Aadhaar System" "Government ID verification" "External"
        llmProvider = softwareSystem "🤖 LLM Provider" "Groq/OpenAI/Ollama" "External"

        # LEVEL 2: CONTAINER - Main System with Containers
        loanSystem = softwareSystem "🏦 Agentic Loan Processing System" "AI-powered loan processing" {
            
            webApp = container "🌐 Streamlit Web App" "User interface" "Python/Streamlit" "Container"
            creditAPI = container "📊 Credit Score API" "Internal credit service" "Python/Flask" "Container"
            aadhaarAPI = container "🆔 Aadhaar API" "Identity verification" "Python/Flask" "Container"
            database = container "🗄️ SQLite Database" "Data storage" "SQLite" "Container"
            fileStorage = container "📂 File Storage" "Document storage" "Local Filesystem" "Container"
            
            # LEVEL 3: COMPONENT - Orchestrator Container with Components
            orchestrator = container "🎭 Loan Agent Orchestrator" "Central coordinator" "Python/LangChain" "Container" {
                
                # Core Orchestration (Level 3)
                loanOrchestrator = component "🎯 LoanAgentOrchestrator" "Main workflow coordinator" "Python Class" "Component"
                agentExecutor = component "🤖 Agent Executor" "Single LangChain agent with tools" "LangChain AgentExecutor" "Component"
                
                # Agent Services (Level 3)
                dataQueryAgent = component "📋 DataQueryAgent" "Data retrieval service" "Python Service" "Component"
                userInteractionAgent = component "💬 UserInteractionAgent" "User communication service" "Python Service" "Component"
                riskAssessmentAgent = component "⚖️ RiskAssessmentAgent" "Risk evaluation service" "Python Service" "Component"
                geoPolicyAgent = component "🌍 GeoPolicyAgent" "Location policy service" "Python Service" "Component"
                agreementAgent = component "📄 AgreementAgent" "Loan agreement service" "Python Service" "Component"
                purposeAgent = component "🎯 PurposeAgent" "Purpose validation service" "Python Service" "Component"
                pdfExtractorAgent = component "📁 PDFExtractorAgent" "PDF processing service" "Python Service" "Component"
                
                # Tool Wrappers (Level 3)
                userInteractionTool = component "💬 UserInteraction Tool" "User communication tool" "LangChain Tool" "Component"
                dataQueryTool = component "📋 DataQuery Tool" "Data retrieval tool" "LangChain Tool" "Component"
                riskAssessmentTool = component "⚖️ RiskAssessment Tool" "Risk evaluation tool" "LangChain Tool" "Component"
                geoPolicyTool = component "🌍 GeoPolicyCheck Tool" "Location policy tool" "LangChain Tool" "Component"
                agreementTool = component "📄 AgreementPresentation Tool" "Agreement generation tool" "LangChain Tool" "Component"
                purposeTool = component "🎯 LoanPurposeAssessment Tool" "Purpose validation tool" "LangChain Tool" "Component"
                pdfExtractorTool = component "📁 PDFSalaryExtractor Tool" "PDF processing tool" "LangChain Tool" "Component"
                creditScoreTool = component "💳 CreditScoreByPAN Tool" "Credit score lookup tool" "LangChain Tool" "Component"
                
                # Data Service (Level 3)
                loanDataService = component "🗄️ LoanDataService" "Central data access" "Python Service" "Component"
                streamlitInputProvider = component "🔄 StreamlitInputProvider" "UI communication manager" "Python Component" "Component"
                
                # LEVEL 4: CODE - Key Classes and Methods (represented as components for visualization)
                loanOrchestratorClass = component "📝 LoanAgentOrchestrator Class" "Main class with methods:\n+process_application()\n+_setup_tools()\n+_user_interaction_with_escalation()" "Python Class" "Code"
                agentExecutorClass = component "📝 AgentExecutor Class" "LangChain class with methods:\n+invoke()\n+run()\n+_execute_tools()" "LangChain Class" "Code"
                dataQueryClass = component "📝 DataQueryAgent Class" "Service class with methods:\n+run()\n+fetch_credit_score_from_api()\n+get_user_data()" "Python Class" "Code"
                userInteractionClass = component "📝 UserInteractionAgent Class" "Service class with methods:\n+run()\n+ask_question()\n+validate_response()" "Python Class" "Code"
                riskAssessmentClass = component "📝 RiskAssessmentAgent Class" "Service class with methods:\n+run()\n+assess_risk()\n+calculate_risk_score()" "Python Class" "Code"
                loanDataServiceClass = component "📝 LoanDataService Class" "Data class with methods:\n+get_user_data()\n+save_user_data()\n+update_loan_status()" "Python Class" "Code"
            }
        }

        # RELATIONSHIPS - All levels combined

        # Level 1: Context relationships
        customer -> webApp "Submits applications"
        loanOfficer -> webApp "Reviews applications"
        admin -> webApp "System management"
        
        # External system relationships
        creditAPI -> creditBureau "Fetches credit data"
        aadhaarAPI -> aadhaarSystem "Verifies identity"
        orchestrator -> llmProvider "AI processing"

        # Level 2: Container relationships
        webApp -> orchestrator "Processes requests"
        orchestrator -> creditAPI "Gets credit scores"
        orchestrator -> aadhaarAPI "Verifies identity"
        orchestrator -> database "Stores data"
        webApp -> fileStorage "Uploads documents"

        # Level 3: Component relationships - Agent Executor to Tools
        loanOrchestrator -> agentExecutor "Coordinates workflow"
        agentExecutor -> userInteractionTool "Uses for user communication"
        agentExecutor -> dataQueryTool "Uses for data retrieval"
        agentExecutor -> riskAssessmentTool "Uses for risk assessment"
        agentExecutor -> geoPolicyTool "Uses for policy checks"
        agentExecutor -> agreementTool "Uses for agreements"
        agentExecutor -> purposeTool "Uses for purpose validation"
        agentExecutor -> pdfExtractorTool "Uses for PDF processing"
        agentExecutor -> creditScoreTool "Uses for credit lookup"
        
        # Level 3: Tool to Service delegation
        userInteractionTool -> userInteractionAgent "Delegates to service"
        dataQueryTool -> dataQueryAgent "Delegates to service"
        riskAssessmentTool -> riskAssessmentAgent "Delegates to service"
        geoPolicyTool -> geoPolicyAgent "Delegates to service"
        agreementTool -> agreementAgent "Delegates to service"
        purposeTool -> purposeAgent "Delegates to service"
        pdfExtractorTool -> pdfExtractorAgent "Delegates to service"
        
        # Level 3: Service dependencies
        dataQueryAgent -> loanDataService "Uses for data access"
        riskAssessmentAgent -> loanDataService "Uses for data access"
        userInteractionAgent -> streamlitInputProvider "Uses for UI communication"
        loanOrchestrator -> streamlitInputProvider "Manages UI communication"
        
        # Level 4: Code-level relationships (Class implementations)
        loanOrchestrator -> loanOrchestratorClass "Implemented by"
        agentExecutor -> agentExecutorClass "Implemented by"
        dataQueryAgent -> dataQueryClass "Implemented by"
        userInteractionAgent -> userInteractionClass "Implemented by"
        riskAssessmentAgent -> riskAssessmentClass "Implemented by"
        loanDataService -> loanDataServiceClass "Implemented by"
    }

    views {
        # Single comprehensive view showing all 4 levels
        container loanSystem "CompleteC4Overview" {
            include *
            autolayout lr
            description "Complete C4 Architecture - All levels in one view: Context (People/External), Container (Apps/Services), Component (Internal Structure), Code (Key Classes)"
        }

        # Alternative focused views for different audiences
        systemContext loanSystem "ContextOnly" {
            include customer loanOfficer admin
            include creditBureau aadhaarSystem llmProvider
            include loanSystem
            autolayout lr
            description "Level 1: System Context - Business view showing external dependencies"
        }

        container loanSystem "ContainerOnly" {
            include webApp orchestrator creditAPI aadhaarAPI database fileStorage
            autolayout lr
            description "Level 2: Container View - Technical view showing major applications and services"
        }

        component orchestrator "ComponentOnly" {
            include loanOrchestrator agentExecutor
            include dataQueryAgent userInteractionAgent riskAssessmentAgent geoPolicyAgent agreementAgent purposeAgent pdfExtractorAgent
            include userInteractionTool dataQueryTool riskAssessmentTool geoPolicyTool agreementTool purposeTool pdfExtractorTool creditScoreTool
            include loanDataService streamlitInputProvider
            autolayout lr
            description "Level 3: Component View - Internal structure showing single agent with multiple tools"
        }

        component orchestrator "CodeLevel" {
            include loanOrchestratorClass agentExecutorClass dataQueryClass userInteractionClass riskAssessmentClass loanDataServiceClass
            autolayout lr
            description "Level 4: Code View - Implementation classes and their key methods"
        }

        # Dynamic view showing the complete flow across all levels
        dynamic loanSystem "CompleteWorkflow" "End-to-end loan processing across all architectural levels" {
            customer -> webApp "1. Submits loan application (Context)"
            webApp -> orchestrator "2. Routes to orchestrator (Container)"
            orchestrator -> database "3. Stores initial data (Container)"
            orchestrator -> aadhaarAPI "4. Verifies identity (Container)"
            aadhaarAPI -> aadhaarSystem "5. Government verification (Context)"
            orchestrator -> creditAPI "6. Gets credit score (Container)"
            creditAPI -> creditBureau "7. External credit check (Context)"
            orchestrator -> webApp "8. Returns final decision (Container)"
            webApp -> customer "9. Displays result (Context)"
            autolayout lr
            description "Complete workflow showing interaction across Context, Container, and Component levels"
        }

        styles {
            element "Person" {
                color #ffffff
                background #08427b
                fontSize 16
                shape Person
            }
            element "External" {
                background #999999
                color #ffffff
                fontSize 12
            }
            element "Container" {
                background #1168bd
                color #ffffff
                fontSize 12
            }
            element "Component" {
                background #85bb65
                color #000000
                fontSize 10
            }
            element "Code" {
                background #f57c00
                color #ffffff
                fontSize 9
            }
            element "Database" {
                shape Cylinder
            }
            relationship "Relationship" {
                color #707070
                fontSize 8
            }
        }
    }

    configuration {
        scope softwaresystem
    }
}
