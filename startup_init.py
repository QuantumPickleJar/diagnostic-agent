#!/usr/bin/env python3
"""
Startup initialization script for the diagnostic agent.
Ensures all models and dependencies are properly loaded before starting the main application.
"""

import os
import sys
import time
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def ensure_sentence_transformers():
    """Ensure SentenceTransformers model is available and working."""
    try:
        logger.info("Initializing SentenceTransformers model...")
        from sentence_transformers import SentenceTransformer
        
        # Download and cache the model
        model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')
        
        # Test the model
        test_embeddings = model.encode(['Startup test'])
        logger.info(f"✅ SentenceTransformers initialized successfully. Embedding shape: {test_embeddings.shape}")
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed to initialize SentenceTransformers: {e}")
        return False

def ensure_semantic_scorer():
    """Ensure semantic scorer is working."""
    try:
        logger.info("Initializing semantic scorer...")
        sys.path.insert(0, '/app')
        
        from semantic_task_scorer import semantic_scorer
        
        if semantic_scorer.embed_ok:
            # Test scoring
            test_score = semantic_scorer.score("test query")
            logger.info(f"✅ Semantic scorer initialized. Test score: {test_score:.3f}")
            return True
        else:
            logger.error("❌ Semantic scorer embeddings not OK")
            return False
            
    except Exception as e:
        logger.error(f"❌ Failed to initialize semantic scorer: {e}")
        return False

def ensure_llama_model():
    """Check if Llama model can be loaded (optional)."""
    try:
        logger.info("Checking Llama model availability...")
        sys.path.insert(0, '/app')
        
        from unified_smart_agent import smart_agent
        
        if smart_agent.model_available:
            logger.info(f"✅ Llama model available at: {smart_agent.model_path}")
        else:
            logger.warning("⚠️ Llama model not available (this is optional)")
            
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed to check Llama model: {e}")
        return False

def main():
    """Main startup initialization."""
    logger.info("🚀 Starting diagnostic agent initialization...")
    
    # Wait a moment for the system to settle
    time.sleep(2)
    
    # Initialize components
    success = True
    
    if not ensure_sentence_transformers():
        success = False
        
    if not ensure_semantic_scorer():
        success = False
        
    if not ensure_llama_model():
        # Llama model is optional, don't fail on this
        pass
    
    if success:
        logger.info("🎉 All components initialized successfully!")
        return 0
    else:
        logger.error("❌ Some components failed to initialize")
        return 1

if __name__ == "__main__":
    sys.exit(main())
