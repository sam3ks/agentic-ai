"""
Loan Purpose Assessment Agent

This agent is responsible for:
1. Taking a user's free-text loan purpose description
2. Matching it against predefined loan purpose categories
3. Determining if the purpose is permitted according to policy
4. Returning the policy details

Implementation uses SentenceTransformer for semantic matching.
"""

import os
import json
import logging
from typing import Dict, Any, List, Optional

import numpy as np
from sentence_transformers import SentenceTransformer

from agentic_ai.core.agent.base_agent import BaseAgent

logger = logging.getLogger(__name__)

class LoanPurposeAssessmentAgent(BaseAgent):
    """
    Agent that analyzes loan purpose statements and classifies them
    according to bank policies.
    
    Uses semantic similarity with SentenceTransformer embeddings to
    match user inputs to predefined categories.
    """
    
    def __init__(self):
        super().__init__()
        self.model = self._load_sentence_transformer()
        self.policy_data = self._load_policy_data()
        self.purpose_categories = list(self.policy_data.keys())
        self.purpose_embeddings = self._precompute_embeddings()
        self.similarity_threshold = 0.6  # Minimum similarity score required for a match
        
    def _load_sentence_transformer(self) -> SentenceTransformer:
        """Load the sentence transformer model."""
        try:
            # Use a smaller model for efficiency if memory is a concern
            return SentenceTransformer('paraphrase-MiniLM-L6-v2')
            
            # For better accuracy, use this instead
            # return SentenceTransformer('all-MiniLM-L12-v2')
        except Exception as e:
            logger.error(f"Error loading SentenceTransformer: {e}")
            raise RuntimeError(f"Failed to load SentenceTransformer: {e}")
    
    def _load_policy_data(self) -> Dict:
        """Load the loan purpose policy data from JSON."""
        try:
            # Construct path to the policy file
            current_dir = os.path.dirname(os.path.abspath(__file__))
            data_dir = os.path.join(os.path.dirname(current_dir), 'data')
            policy_path = os.path.join(data_dir, 'loan_purpose_policy.json')
            
            with open(policy_path, 'r') as f:
                policy_data = json.load(f)
                
            logger.info(f"Loaded {len(policy_data)} purpose categories from policy file")
            return policy_data
        except Exception as e:
            logger.error(f"Error loading policy data: {e}")
            raise ValueError(f"Could not load policy data: {e}")
    
    def _precompute_embeddings(self) -> np.ndarray:
        """Precompute embeddings for all purpose categories for faster matching."""
        try:
            return self.model.encode(self.purpose_categories)
        except Exception as e:
            logger.error(f"Error precomputing embeddings: {e}")
            raise RuntimeError(f"Failed to compute embeddings: {e}")
    
    def _match_purpose_category(self, user_purpose: str) -> Optional[str]:
        """
        Match user's purpose statement to a predefined category.
        
        Args:
            user_purpose: The user's description of their loan purpose
            
        Returns:
            The matched category name or None if no good match found
        """
        try:
            # Encode the user's purpose description
            user_embedding = self.model.encode([user_purpose])
            
            # Calculate cosine similarity between user input and all categories
            similarities = np.dot(user_embedding, self.purpose_embeddings.T)[0]
            
            # Find the index of the highest similarity score
            best_match_idx = np.argmax(similarities)
            best_match_score = similarities[best_match_idx]
            
            logger.debug(f"Best match: '{self.purpose_categories[best_match_idx]}' with score {best_match_score}")
            
            # Check if the match meets our threshold
            if best_match_score >= self.similarity_threshold:
                return self.purpose_categories[best_match_idx]
                
            # No good match found
            return None
            
        except Exception as e:
            logger.error(f"Error in purpose matching: {e}")
            return None
    
    def run(self, purpose: str) -> Dict[str, Any]:
        """
        Process a loan purpose statement and return policy assessment.
        
        Args:
            purpose: User's stated purpose for the loan
            
        Returns:
            Dictionary containing matched category and policy details
        """
        logger.info(f"Processing loan purpose: '{purpose}'")
        
        try:
            # Step 1 & 2: Match purpose to predefined category
            matched_category = self._match_purpose_category(purpose)
            
            if not matched_category:
                logger.warning(f"No clear category match found for: '{purpose}'")
                return {
                    "matched_category": None,
                    "policy_details": None,
                    "message": "Could not clearly determine loan purpose category. Please provide more specific details."
                }
            
            # Step 3: Retrieve policy information
            policy_details = self.policy_data.get(matched_category)
            
            # Step 4: Format and return the result
            result = {
                "matched_category": matched_category,
                "policy_details": policy_details
            }
            
            # Add convenience summary at the top level
            result["is_permitted"] = policy_details.get("eligibility") == "permitted"
            
            logger.info(f"Purpose '{purpose}' matched to '{matched_category}' "
                        f"(Permitted: {result['is_permitted']})")
                        
            return result
            
        except Exception as e:
            logger.error(f"Error processing loan purpose: {e}")
            return {
                "error": str(e),
                "message": "An error occurred while processing your loan purpose."
            }
